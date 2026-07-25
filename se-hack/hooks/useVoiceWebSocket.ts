import { useEffect, useRef, useState, useCallback } from "react";
import { backendWebSocketBaseUrl } from "@/lib/backend";

export interface ProsodyMetrics {
  source?: string;
  confidence?: number;
  nervousness?: number;
  energy?: number;
  top_emotions?: { name: string; score: number }[];
  pace_wpm?: number;
  pace_score?: number;
  filler_count?: number;
  total_words?: number;
  filler_ratio?: number;
  clarity_score?: number;
  speech_duration_seconds?: number;
}

export interface VoiceOutput {
  acoustic?: {
    pitch: number;
    energy: number;
    speaking_rate: number;
  };
  semantic?: {
    insight: string;
    stress_level: string;
    confidence_score: number;
    time_range?: number[];
    words?: string[];
  };
  final_summary?: {
    overall_summary: string;
    key_moments: { time: string; description: string }[];
  };
  prosody?: ProsodyMetrics | null;
}

export interface TranscriptWord {
  word: string;
  start: number;
  end: number;
  timestamp: string;
}
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: {
    length: number;
    [index: number]: {
      isFinal: boolean;
      [index: number]: {
        transcript: string;
      };
    };
  };
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

type BrowserRecognition = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function getBrowserRecognitionCtor(): (new () => BrowserRecognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as typeof window & {
    SpeechRecognition?: new () => BrowserRecognition;
    webkitSpeechRecognition?: new () => BrowserRecognition;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function toPcm16At16k(input: Float32Array, sourceRate: number): ArrayBuffer {
  const targetRate = 16000;
  if (sourceRate === targetRate) {
    const pcm = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm.buffer;
  }

  const ratio = sourceRate / targetRate;
  const outLen = Math.floor(input.length / ratio);
  const pcm = new Int16Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const srcIdx = Math.floor(i * ratio);
    const s = Math.max(-1, Math.min(1, input[srcIdx] ?? 0));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return pcm.buffer;
}

export function useVoiceWebSocket(
  isRecording: boolean,
  sharedStream?: MediaStream | null,
) {
  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const ownsStreamRef = useRef(false);
  const recognitionRef = useRef<BrowserRecognition | null>(null);
  const useBrowserSttRef = useRef(false);
  const backendTranscriptRef = useRef(false);

  const [metrics, setMetrics] = useState<VoiceOutput>({});
  const [transcript, setTranscript] = useState<TranscriptWord[]>([]);
  const [insights, setInsights] = useState<VoiceOutput["semantic"][]>([]);
  const [sttError, setSttError] = useState<string | null>(null);
  const [sttMode, setSttMode] = useState<"backend" | "browser" | "idle">(
    "idle",
  );

  const sendEmotionContext = useCallback(
    (
      emotion: string,
      confidence: number,
      emotionBreakdown?: Record<string, number>,
      extraVideoMetrics?: unknown,
    ) => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(
          JSON.stringify({
            type: "emotion_context",
            emotion,
            confidence,
            emotion_breakdown: emotionBreakdown,
            extra_video_metrics: extraVideoMetrics,
          }),
        );
      }
    },
    [],
  );

  const applyBrowserTranscript = useCallback(
    (text: string, interim: boolean) => {
      const words = text.trim().split(/\s+/).filter(Boolean);
      if (words.length === 0) return;
      setTranscript(
        words.map((word, i) => ({
          word,
          start: i * 0.3,
          end: (i + 1) * 0.3,
          timestamp: formatTime(i * 0.3),
        })),
      );
      if (!interim) {
        setSttError(null);
      }
    },
    [],
  );

  const stopBrowserRecognition = useCallback(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return;
    recognition.onresult = null;
    recognition.onerror = null;
    recognition.onend = null;
    try {
      recognition.stop();
    } catch {
      try {
        recognition.abort();
      } catch {
        /* ignore */
      }
    }
    recognitionRef.current = null;
  }, []);

  const startBrowserRecognition = useCallback(() => {
    const Ctor = getBrowserRecognitionCtor();
    if (!Ctor) {
      setSttError(
        "Speech recognition unavailable. Use Chrome/Edge or type your answer.",
      );
      return;
    }

    stopBrowserRecognition();
    const recognition = new Ctor();
    recognitionRef.current = recognition;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let finalText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0]?.transcript ?? "";
        if (event.results[i].isFinal) {
          finalText += `${piece} `;
        } else {
          interim += piece;
        }
      }
      const text = (finalText || interim).trim();
      if (text) {
        applyBrowserTranscript(text, !finalText.trim());
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error !== "aborted" && event.error !== "no-speech") {
        setSttError(`Mic recognition error: ${event.error}`);
      }
    };

    recognition.onend = () => {
      if (useBrowserSttRef.current && recognitionRef.current === recognition) {
        try {
          recognition.start();
        } catch {
          /* ignore restart race */
        }
      }
    };

    try {
      recognition.start();
      useBrowserSttRef.current = true;
      setSttMode("browser");
      setSttError(null);
    } catch {
      setSttError("Could not start browser speech recognition.");
    }
  }, [applyBrowserTranscript, stopBrowserRecognition]);

  const startMicCapture = useCallback(
    async (ws: WebSocket) => {
      try {
        let stream = sharedStream;
        if (!stream || stream.getAudioTracks().length === 0) {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          ownsStreamRef.current = true;
        } else {
          ownsStreamRef.current = false;
        }
        streamRef.current = stream;

        const AudioContextClass =
          window.AudioContext ||
          (
            window as typeof window & {
              webkitAudioContext: typeof AudioContext;
            }
          ).webkitAudioContext;
        const audioContext = new AudioContextClass();
        audioContextRef.current = audioContext;

        if (audioContext.state === "suspended") {
          await audioContext.resume();
        }

        const source = audioContext.createMediaStreamSource(stream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;
        source.connect(processor);
        processor.connect(audioContext.destination);

        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN) return;
          const inputData = e.inputBuffer.getChannelData(0);
          ws.send(toPcm16At16k(inputData, audioContext.sampleRate));
        };
      } catch (err) {
        console.error("Microphone access denied:", err);
        setSttError(
          "Microphone access denied. Allow mic permission or type your answer.",
        );
        startBrowserRecognition();
      }
    },
    [sharedStream, startBrowserRecognition],
  );

  const stopMicCapture = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
      processorRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      void audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (streamRef.current && ownsStreamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    streamRef.current = null;
    ownsStreamRef.current = false;
  }, []);

  useEffect(() => {
    if (!isRecording) {
      useBrowserSttRef.current = false;
      backendTranscriptRef.current = false;
      stopBrowserRecognition();
      stopMicCapture();
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send("STOP");
      }
      queueMicrotask(() => setSttMode("idle"));
      return;
    }

    backendTranscriptRef.current = false;
    const cancelled = { current: false };
    let ws: WebSocket | null = null;
    let browserFallbackTimer: number | undefined;

    (async () => {
      let token = "";
      try {
        const res = await fetch("/api/auth/ws-token", { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          token = data.token ?? "";
        }
      } catch {
        /* fall through, backend will reject and browser STT will kick in */
      }

      if (cancelled.current) return;

      const wsUrl = `${backendWebSocketBaseUrl}/voice/stream?token=${encodeURIComponent(token)}`;
      const socket = new WebSocket(wsUrl);
      ws = socket;
      socketRef.current = socket;

      browserFallbackTimer = window.setTimeout(() => {
        if (!backendTranscriptRef.current && isRecording) {
          startBrowserRecognition();
        }
      }, 2500);

      socket.onopen = () => {
        setSttMode("backend");
        void startMicCapture(socket);
      };

      socket.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "transcript_word") {
            backendTranscriptRef.current = true;
            useBrowserSttRef.current = false;
            stopBrowserRecognition();
            setSttMode("backend");
            setTranscript((prev) => [
              ...prev,
              {
                word: data.word,
                start: data.start,
                end: data.end,
                timestamp: formatTime(data.start),
              },
            ]);
          }

          if (data.type === "transcript_interim" && typeof data.text === "string") {
            backendTranscriptRef.current = true;
            applyBrowserTranscript(data.text, true);
          }

          if (data.type === "stt_unavailable" || (data.type === "error" && data.message)) {
            startBrowserRecognition();
          }

          if (data.type === "periodic_insight") {
            setMetrics((prev) => ({
              ...prev,
              acoustic: data.acoustic || prev.acoustic,
              semantic: data.semantic || prev.semantic,
            }));
            if (data.semantic) {
              setInsights((prev) => [...prev, data.semantic]);
            }
          }

          if (data.type === "final_summary") {
            setMetrics((prev) => ({
              ...prev,
              final_summary: data.content,
              prosody: data.prosody ?? prev.prosody ?? null,
            }));
          }
        } catch (e) {
          console.error("Failed to parse WS data", e);
        }
      };

      socket.onerror = () => {
        startBrowserRecognition();
      };

      socket.onclose = (event: CloseEvent) => {
        window.clearTimeout(browserFallbackTimer);
        if (event.code === 1008) {
          setSttError("Voice session unauthorized. Try logging in again.");
        } else if (isRecording && !backendTranscriptRef.current) {
          startBrowserRecognition();
        }
      };
    })();

    return () => {
      cancelled.current = true;
      window.clearTimeout(browserFallbackTimer);
      useBrowserSttRef.current = false;
      stopBrowserRecognition();
      stopMicCapture();
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
      if (socketRef.current === ws) {
        socketRef.current = null;
      }
    };
  }, [
    isRecording,
    startMicCapture,
    stopMicCapture,
    startBrowserRecognition,
    stopBrowserRecognition,
    applyBrowserTranscript,
  ]);

  const resetState = useCallback(() => {
    setMetrics({});
    setTranscript([]);
    setInsights([]);
    setSttError(null);
    setSttMode("idle");
    backendTranscriptRef.current = false;
  }, []);

  const clearTranscript = useCallback(() => {
    setTranscript([]);
  }, []);

  const getTranscriptText = useCallback(() => {
    return transcript.map((w) => w.word).join(" ");
  }, [transcript]);

  return {
    metrics,
    transcript,
    insights,
    sttError,
    sttMode,
    sendEmotionContext,
    resetState,
    clearTranscript,
    getTranscriptText,
  };
}
