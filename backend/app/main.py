"""
Voice Agent – main entry point.

For the MVP we expose a simple FastAPI + WebSocket server that:
1. Accepts text messages (or base64 audio later)
2. Runs them through the LLM + tools
3. Returns text + optional TTS audio

This keeps the first version easy to run and debug.
Full Pipecat real-time pipeline can be added on top later.
"""

from __future__ import annotations

import base64
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.agent.llm import LLMClient
from app.config import get_settings
from app.documents.loader import save_uploaded_file
from app.documents.rag import rag_service
from app.documents.dictation import prepare_dictation
from app.tts.edge_tts import EdgeTTS


settings = get_settings()
llm = LLMClient()
tts = EdgeTTS()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Voice Agent starting…")
    settings.ensure_dirs()
    yield
    logger.info("Voice Agent shutting down")


app = FastAPI(title="Voice Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "llm_model": settings.llm_model}


@app.post("/chat")
async def chat(payload: dict[str, Any]):
    """Simple text chat endpoint (useful for testing without voice)."""
    text = payload.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    response = await llm.chat(text)

    # Detect dictation request
    if response.startswith("__DICTATE__:"):
        parts = response.split(":", 2)
        filename = parts[1] if len(parts) > 1 else ""
        section = parts[2] if len(parts) > 2 else "full"
        full_text = rag_service.get_full_text(filename)
        if not full_text:
            return {"text": f"Could not find document '{filename}'."}
        chunks = prepare_dictation(full_text, section)
        return {
            "text": f"Starting dictation of {filename}…",
            "dictation_chunks": chunks,
        }

    return {"text": response}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document and index it for RAG + dictation."""
    content = await file.read()
    path = save_uploaded_file(file.filename or "upload.bin", content, settings.documents_dir)
    result = rag_service.ingest_file(path)
    return {"filename": path.name, "message": result}


@app.get("/documents")
async def list_documents():
    docs = [p.name for p in settings.documents_dir.glob("*") if p.is_file()]
    return {"documents": docs}


@app.post("/tts")
async def text_to_speech(payload: dict[str, Any]):
    """Convert text to speech and return base64 MP3."""
    text = payload.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)

    audio_bytes = await tts.synthesize(text)
    if not audio_bytes:
        return JSONResponse({"error": "TTS failed"}, status_code=500)

    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return {"audio_base64": b64, "format": "mp3"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Simple WebSocket for real-time text exchange.
    Protocol (JSON):
      Client → Server: {"type": "text", "text": "hello"}
      Server → Client: {"type": "response", "text": "..."}
                       {"type": "audio", "audio_base64": "..."}  (optional)
    """
    await ws.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            if msg.get("type") == "text":
                user_text = msg.get("text", "").strip()
                if not user_text:
                    continue

                response = await llm.chat(user_text)

                # Handle dictation special case
                if response.startswith("__DICTATE__:"):
                    parts = response.split(":", 2)
                    filename = parts[1] if len(parts) > 1 else ""
                    section = parts[2] if len(parts) > 2 else "full"
                    full_text = rag_service.get_full_text(filename)
                    if full_text:
                        chunks = prepare_dictation(full_text, section)
                        await ws.send_json({
                            "type": "dictation_start",
                            "filename": filename,
                            "chunks": chunks,
                        })
                    else:
                        await ws.send_json({
                            "type": "response",
                            "text": f"Could not find document '{filename}'.",
                        })
                    continue

                await ws.send_json({"type": "response", "text": response})

                # Optionally generate TTS audio
                if msg.get("want_audio", True):
                    audio = await tts.synthesize(response)
                    if audio:
                        b64 = base64.b64encode(audio).decode("utf-8")
                        await ws.send_json({
                            "type": "audio",
                            "audio_base64": b64,
                            "format": "mp3",
                        })

            elif msg.get("type") == "reset":
                llm.reset()
                await ws.send_json({"type": "info", "message": "Conversation reset"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
