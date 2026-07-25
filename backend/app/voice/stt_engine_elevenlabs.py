import asyncio
import base64
import json
import logging
import os
from typing import Callable

import websockets

logger = logging.getLogger(__name__)

# ElevenLabs Scribe v2 Realtime STT.
# Docs: wss://api.elevenlabs.io/v1/speech-to-text/realtime
class ElevenLabsEngine:
    def __init__(self, on_word: Callable[[dict], None]):
        self.url = (
            "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
            "?model_id=scribe_v2_realtime"
            "&audio_format=pcm_16000"
            "&sample_rate=16000"
            "&commit_strategy=vad"
            "&include_timestamps=true"
        )
        self.api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
        self.ws = None
        self.on_word = on_word
        self.receive_task = None
        self.last_error: str | None = None
        self._last_interim = ""

    async def connect(self) -> bool:
        self.last_error = None
        if not self.api_key:
            self.last_error = "ELEVENLABS_API_KEY is not set in backend/.env"
            logger.error(self.last_error)
            return False

        headers = {"xi-api-key": self.api_key}
        try:
            self.ws = await asyncio.wait_for(
                websockets.connect(self.url, additional_headers=headers, ping_interval=20, ping_timeout=20),
                timeout=15,
            )
            logger.info("Connected to ElevenLabs streaming STT")
            self.receive_task = asyncio.create_task(self._listen())
            return True
        except Exception as exc:
            self.last_error = str(exc)
            logger.error("Failed to connect to ElevenLabs STT: %s", exc)
            self.ws = None
            return False

    async def send_audio(self, pcm_bytes: bytes):
        if not self.ws:
            return
        try:
            payload = {
                "audio_base_64": base64.b64encode(pcm_bytes).decode("ascii"),
                "message_type": "input_audio_chunk",
            }
            await self.ws.send(json.dumps(payload))
        except websockets.exceptions.ConnectionClosed:
            self.ws = None

    async def close(self):
        try:
            if self.ws:
                await self.ws.close()
        except Exception:
            pass

        if self.receive_task:
            self.receive_task.cancel()
            self.receive_task = None
        self.ws = None

    async def _listen(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                msg_type = data.get("message_type")

                if msg_type == "partial_transcript":
                    text = (data.get("text") or "").strip()
                    if text and text != self._last_interim:
                        self._last_interim = text
                        self.on_word({"word": text, "start": 0, "end": 0, "interim": True})

                elif msg_type in ("committed_transcript_with_timestamps", "final_transcript_with_timestamps"):
                    self._last_interim = ""
                    words = data.get("words") or []
                    for w in words:
                        self.on_word(
                            {
                                "word": w.get("text") or w.get("word"),
                                "start": w.get("start", 0),
                                "end": w.get("end", 0),
                                "interim": False,
                            }
                        )

                elif msg_type in ("committed_transcript", "final_transcript") and not data.get("words"):
                    # No timestamps in this event (include_timestamps message hasn't arrived yet);
                    # skip here, the *_with_timestamps event carries the word-level data we need.
                    pass

                elif msg_type in (
                    "scribeError",
                    "scribe_error",
                    "scribeAuthError",
                    "scribeQuotaExceededError",
                    "scribeRateLimitedError",
                    "rate_limited",
                ):
                    logger.warning("ElevenLabs STT error event: %s", data)

        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            logger.warning("ElevenLabs STT connection closed")
        except Exception as exc:
            logger.error("ElevenLabs listen error: %s", exc)