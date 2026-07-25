import asyncio
import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
import numpy as np

from app.auth.jwt import decode_token
from app.db import AsyncSessionLocal
from app.models.user import User
from .audio_buffer import AudioBuffer
from .audio_features import extract_features
# We now import the Deepgram Engine from the STT layer
from .stt_engine_elevenlabs import ElevenLabsEngine
from .llm_engine import get_periodic_insights, get_final_summary
from .hume_analyzer import analyze_prosody, compute_speech_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Stream"])

async def get_ws_user(websocket: WebSocket):
    access_token = websocket.cookies.get("access_token")
    if not access_token:
        access_token = websocket.query_params.get("token")

    if not access_token:
        return None

    try:
        payload = decode_token(token=access_token, expected_type="access")
        user_uuid = uuid.UUID(payload["user_id"])
    except Exception as e:
        logger.error(f"WS auth error: {e}")
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_uuid))
        return result.scalar_one_or_none()

@router.websocket("/stream")
async def voice_stream(websocket: WebSocket):
    await websocket.accept()
    
    user = await get_ws_user(websocket)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized")
        return

    logger.info(f"User {user.id} connected to voice stream.")

    buffer = AudioBuffer(sample_rate=16000)
    
    # State tracking
    acoustic_pool = np.array([], dtype=np.float32)
    semantic_words = []
    
    session_words = []
    session_insights = []

    # Full-session audio for Hume prosody analysis (capped at ~15 min @16kHz)
    session_audio_chunks: list[np.ndarray] = []
    session_audio_samples = 0
    max_session_audio_samples = 16000 * 60 * 15
    
    # Emotion context from video analysis (populated by frontend emotion bridge)
    emotion_context_buffer = []
    latest_emotion = None

    # Starlette websockets do not allow concurrent send() calls
    ws_lock = asyncio.Lock()

    async def safe_send(data: dict):
        try:
            async with ws_lock:
                await websocket.send_text(json.dumps(data))
        except Exception:
            pass

    def on_word_received(word_data: dict):
        if not word_data.get("word"):
            return

        is_interim = bool(word_data.get("interim"))
        if not is_interim:
            print(f"[Deepgram-Stream] {word_data['word']}", end=" ", flush=True)
            semantic_words.append(word_data)
            session_words.append(word_data)

        try:
            if is_interim:
                asyncio.get_event_loop().create_task(
                    safe_send({
                        "type": "transcript_interim",
                        "text": word_data.get("word", ""),
                        "start": word_data.get("start", 0),
                    })
                )
            else:
                asyncio.get_event_loop().create_task(
                    safe_send({
                        "type": "transcript_word",
                        "word": word_data.get("word", ""),
                        "start": word_data.get("start", 0),
                        "end": word_data.get("end", 0),
                    })
                )
        except Exception:
            pass

    deepgram = ElevenLabsEngine(on_word=on_word_received)
    stt_ready = await deepgram.connect()
    if not stt_ready:
        detail = deepgram.last_error or "ElevenLabs STT connection failed"
        logger.warning("STT unavailable for user %s: %s", user.id, detail)
        await safe_send({
            "type": "stt_unavailable",
            "message": f"Server STT offline ({detail}). Using browser speech recognition.",
        })

    async def process_chunks():
        nonlocal acoustic_pool, semantic_words, session_words, session_insights, latest_emotion, session_audio_samples
        try:
            while True:
                await asyncio.sleep(0.5)
                chunk = await buffer.get_all()
                if chunk is not None:
                    acoustic_pool = np.concatenate((acoustic_pool, chunk))
                    if session_audio_samples < max_session_audio_samples:
                        session_audio_chunks.append(chunk)
                        session_audio_samples += len(chunk)
                
                # 1. Acoustic Loop (~2 seconds = 32000 samples)
                if len(acoustic_pool) >= 32000:
                    extract_chunk = acoustic_pool.copy()
                    acoustic_pool = np.array([], dtype=np.float32) # Flush pool
                    
                    features = await extract_features(extract_chunk, sample_rate=16000)
                    
                    await safe_send({
                        "type": "periodic_insight",
                        "acoustic": {
                            "pitch": round(features["pitch"] if not np.isnan(features["pitch"]) else 0, 1),
                            "energy": round(features["energy"], 3),
                            "speaking_rate": round(features["speaking_rate"], 3)
                        }
                    })

                # 2. Semantic Loop (~10 seconds gap tracked by exact word-level timings)
                if len(semantic_words) > 0:
                    first_time = semantic_words[0].get("start", 0)
                    last_time = semantic_words[-1].get("end", 0)
                    
                    if last_time - first_time >= 10.0:
                        # Extract the block
                        words_block = list(semantic_words)
                        semantic_words.clear()
                        
                        text = " ".join([w["word"] for w in words_block if w.get("word")])
                        print(f"\n[SEMANTIC BUFFER FLUSH] 10s Transcript: '{text}'")
                        
                        # Build emotion context snapshot for this window
                        emotion_snapshot = None
                        if latest_emotion:
                            emotion_snapshot = latest_emotion.copy()
                        
                        insight = await get_periodic_insights(
                            text,
                            words_timestamps=words_block,
                            emotion_context=emotion_snapshot,
                        )
                        print(f"[LLM ENGINE] Analyzed Result: {json.dumps(insight)}")
                        if insight:
                            session_insights.append(insight)
                            await safe_send({
                                "type": "periodic_insight",
                                "semantic": insight
                            })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in processor task: {e}")

    processor_task = asyncio.create_task(process_chunks())

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                # Tunnel to Audio Buffer for Acoustic Math
                await buffer.add_data(message["bytes"])
                # Tunnel to Deepgram for Streaming Semantic Extrapolation
                await deepgram.send_audio(message["bytes"])
            elif "text" in message and message["text"]:
                text_data = message["text"]
                
                if text_data == "STOP":
                    print("[VOICE] Stop command received. Terminating streams and running final analysis...")
                    break
                
                # Handle JSON messages (emotion context from video analysis)
                try:
                    parsed = json.loads(text_data)
                    if parsed.get("type") == "emotion_context":
                        latest_emotion = {
                            "emotion": parsed.get("emotion", "unknown"),
                            "confidence": parsed.get("confidence", 0),
                            "emotion_breakdown": parsed.get("emotion_breakdown", {}),
                            "extra_video_metrics": parsed.get("extra_video_metrics", {}),
                        }
                        emotion_context_buffer.append(latest_emotion)
                        # Keep only last 30 snapshots (~60s at 2s intervals)
                        if len(emotion_context_buffer) > 30:
                            emotion_context_buffer.pop(0)
                except (json.JSONDecodeError, ValueError):
                    pass
                
    except WebSocketDisconnect:
        print(f"[VOICE] User {user.id} disconnected unexpectedly.")
    except Exception as e:
        print(f"[VOICE] WebSocket error: {e}")
    finally:
        processor_task.cancel()
        await deepgram.close()
        
        # Do final session analysis if gracefully stopped
        try:
            print(f"[VOICE] Extracting Final Session Summary from {len(session_words)} words...")
            if len(session_words) > 0:
                full_text = " ".join([w["word"] for w in session_words if w.get("word")])
                
                def format_sec(sec):
                    m = int(sec // 60)
                    s = int(sec % 60)
                    return f"{m}:{s:02d}"

                # Format session insights into clean strings so LLM doesn't hallucinate time conversions
                formatted_insights = []
                for ins in session_insights:
                    fi = ins.copy()
                    if "time_range" in fi and isinstance(fi["time_range"], list):
                        fi["time_str"] = f"{format_sec(fi['time_range'][0])}-{format_sec(fi['time_range'][1])}"
                    formatted_insights.append(fi)

                # Build aggregated emotion timeline for final summary
                emotion_timeline = []
                for i, ctx in enumerate(emotion_context_buffer):
                    time_sec = i * 2
                    emotion_timeline.append({
                        "time_window": format_sec(time_sec),
                        "emotion": ctx.get("emotion", "unknown"),
                        "confidence": ctx.get("confidence", 0),
                        "visual_behavior": ctx.get("extra_video_metrics", {})
                    })
                
                final_summary = await get_final_summary(
                    full_text,
                    formatted_insights,
                    emotion_timeline=emotion_timeline,
                )
            else:
                final_summary = {
                    "overall_summary": "No speech was detected during this interview session.",
                    "key_moments": []
                }
            
            print(f"[LLM ENGINE] Final Session Summary: {json.dumps(final_summary)}")

            # ── Hume prosody + speech pace metrics (real ML, graceful skip) ──
            prosody_payload = None
            try:
                speech_metrics = compute_speech_metrics(session_words)
                hume_result = None
                if session_audio_chunks:
                    session_audio = np.concatenate(session_audio_chunks)
                    hume_result = await asyncio.wait_for(
                        analyze_prosody(session_audio, sample_rate=16000),
                        timeout=45,
                    )
                if hume_result or speech_metrics:
                    prosody_payload = {**(hume_result or {}), **(speech_metrics or {})}
                    print(f"[VOICE] Prosody payload: {json.dumps(prosody_payload)[:400]}")
            except asyncio.TimeoutError:
                print("[VOICE] Hume prosody analysis timed out; continuing without it.")
            except Exception as ex:
                print(f"[VOICE] Prosody analysis failed: {ex}")

            try:
                await websocket.send_text(json.dumps({
                    "type": "final_summary",
                    "content": final_summary,
                    "prosody": prosody_payload,
                }))
                print("[VOICE] Final summary successfully pushed to client.")
            except Exception as ex:
                print(f"[VOICE] Could not send final summary to client (probably disconnected): {ex}")
        except Exception as e:
            print(f"[VOICE] Error generating final summary: {e}")
            
        try:
            await websocket.close()
        except:
            pass