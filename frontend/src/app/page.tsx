"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Mic,
  MicOff,
  Upload,
  FileText,
  Send,
  Volume2,
  Trash2,
  Loader2,
} from "lucide-react";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:7860";

type Message = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
};

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "system",
      text: "Hello! I’m your voice agent. You can talk to me, upload documents, ask questions about them, or ask me to read them aloud.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [documents, setDocuments] = useState<string[]>([]);
  const [wsConnected, setWsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load document list
  const refreshDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND}/documents`);
      const data = await res.json();
      setDocuments(data.documents || []);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  // WebSocket connection
  useEffect(() => {
    const wsUrl = BACKEND.replace(/^http/, "ws") + "/ws";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "response") {
          setMessages((prev) => [
            ...prev,
            { id: Date.now().toString(), role: "assistant", text: msg.text },
          ]);
          setIsProcessing(false);

          // Play audio if provided
          if (msg.audio_base64) {
            playAudio(msg.audio_base64);
          }
        }

        if (msg.type === "audio" && msg.audio_base64) {
          playAudio(msg.audio_base64);
        }

        if (msg.type === "dictation_start" && msg.chunks) {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now().toString(),
              role: "assistant",
              text: `Reading “${msg.filename}”…`,
            },
          ]);
          // Speak chunks one by one using browser TTS as fallback
          speakChunks(msg.chunks);
          setIsProcessing(false);
        }
      } catch {
        /* ignore */
      }
    };

    return () => ws.close();
  }, []);

  function playAudio(base64: string) {
    const audio = new Audio(`data:audio/mp3;base64,${base64}`);
    audio.play().catch(() => {
      // fallback to browser TTS if needed
    });
  }

  function speakChunks(chunks: string[]) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    chunks.forEach((chunk, i) => {
      const utter = new SpeechSynthesisUtterance(chunk);
      utter.rate = 1.0;
      utter.pitch = 1.0;
      if (i === 0) window.speechSynthesis.speak(utter);
      else {
        // chain them
        const prev = window.speechSynthesis;
        // simple sequential via onend would be better; for MVP we just speak first few
      }
    });
    // Speak all sequentially
    let idx = 0;
    const speakNext = () => {
      if (idx >= chunks.length) return;
      const u = new SpeechSynthesisUtterance(chunks[idx]);
      u.onend = () => {
        idx++;
        speakNext();
      };
      window.speechSynthesis.speak(u);
    };
    speakNext();
  }

  // Browser Speech Recognition (free STT fallback)
  function startListening() {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Use Chrome or Edge.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
      sendMessage(transcript);
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setIsListening(false);
  }

  async function sendMessage(text?: string) {
    const content = (text || input).trim();
    if (!content) return;

    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role: "user", text: content },
    ]);
    setInput("");
    setIsProcessing(true);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: "text", text: content, want_audio: true })
      );
    } else {
      // Fallback to HTTP
      try {
        const res = await fetch(`${BACKEND}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: content }),
        });
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), role: "assistant", text: data.text },
        ]);
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            role: "system",
            text: "Could not reach the backend. Is it running?",
          },
        ]);
      } finally {
        setIsProcessing(false);
      }
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${BACKEND}/upload`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "system",
          text: data.message || `Uploaded ${file.name}`,
        },
      ]);
      refreshDocuments();
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "system",
          text: "Upload failed. Is the backend running?",
        },
      ]);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600">
            <Volume2 className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Voice Agent</h1>
            <p className="text-xs text-slate-400">
              {wsConnected ? "Connected" : "Disconnected"} · Personal AI
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700">
            <Upload className="h-4 w-4" />
            Upload Doc
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              onChange={handleUpload}
            />
          </label>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar – Documents */}
        <aside className="hidden w-64 flex-shrink-0 border-r border-slate-800 bg-slate-900/50 p-4 md:block">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
            <FileText className="h-4 w-4" /> Documents
          </h2>
          {documents.length === 0 ? (
            <p className="text-xs text-slate-500">No documents yet. Upload a PDF or DOCX.</p>
          ) : (
            <ul className="space-y-1">
              {documents.map((doc) => (
                <li
                  key={doc}
                  className="truncate rounded px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
                  title={doc}
                >
                  {doc}
                </li>
              ))}
            </ul>
          )}
        </aside>

        {/* Chat area */}
        <main className="flex flex-1 flex-col">
          <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="mx-auto max-w-2xl space-y-4">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex ${
                    m.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                      m.role === "user"
                        ? "bg-blue-600 text-white"
                        : m.role === "system"
                        ? "bg-slate-800 text-slate-300"
                        : "bg-slate-800 text-slate-100"
                    }`}
                  >
                    {m.text}
                  </div>
                </div>
              ))}
              {isProcessing && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 rounded-2xl bg-slate-800 px-4 py-2.5 text-sm text-slate-400">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Thinking…
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input bar */}
          <div className="border-t border-slate-800 px-4 py-4">
            <div className="mx-auto flex max-w-2xl items-center gap-2">
              <button
                onClick={isListening ? stopListening : startListening}
                className={`flex h-11 w-11 items-center justify-center rounded-full transition ${
                  isListening
                    ? "bg-red-600 hover:bg-red-500"
                    : "bg-slate-800 hover:bg-slate-700"
                }`}
                title={isListening ? "Stop listening" : "Start voice input"}
              >
                {isListening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
              </button>

              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder="Type a message or use the microphone…"
                className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm outline-none placeholder:text-slate-500 focus:border-blue-500"
              />

              <button
                onClick={() => sendMessage()}
                disabled={isProcessing || !input.trim()}
                className="flex h-11 w-11 items-center justify-center rounded-full bg-blue-600 transition hover:bg-blue-500 disabled:opacity-40"
              >
                <Send className="h-5 w-5" />
              </button>
            </div>
            <p className="mx-auto mt-2 max-w-2xl text-center text-xs text-slate-500">
              Try: “What documents do I have?” · “Read the report” · “What is 15% of 240?”
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
