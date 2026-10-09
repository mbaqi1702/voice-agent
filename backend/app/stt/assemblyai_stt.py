"""
AssemblyAI streaming STT integration (free tier available).
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Optional

from loguru import logger

from app.config import get_settings


class AssemblyAISTT:
    """
    Thin wrapper around AssemblyAI real-time transcription.
    For MVP we also provide a simple file-based transcribe method.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.assemblyai_api_key
        if not self.api_key:
            logger.warning("ASSEMBLYAI_API_KEY not set – STT will not work until configured")

    async def transcribe_file(self, audio_path: str) -> str:
        """Transcribe a complete audio file (useful for testing)."""
        try:
            import assemblyai as aai
            aai.settings.api_key = self.api_key
            transcriber = aai.Transcriber()
            transcript = await asyncio.to_thread(transcriber.transcribe, audio_path)
            return transcript.text or ""
        except Exception as e:
            logger.error(f"AssemblyAI transcription failed: {e}")
            return ""

    async def transcribe_bytes(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw audio bytes (WAV/PCM)."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp = f.name

        try:
            return await self.transcribe_file(tmp)
        finally:
            Path(tmp).unlink(missing_ok=True)
