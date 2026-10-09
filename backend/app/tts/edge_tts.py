"""
Free TTS using Microsoft Edge's online neural voices (edge-tts).
No API key required.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Optional

from loguru import logger

from app.config import get_settings


class EdgeTTS:
    def __init__(self) -> None:
        settings = get_settings()
        self.voice = settings.tts_voice or "en-US-AriaNeural"

    async def synthesize(self, text: str, output_path: Optional[str] = None) -> bytes:
        """
        Convert text to speech and return MP3 bytes.
        Optionally also write to a file.
        """
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)
            audio_data = b""

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if output_path:
                Path(output_path).write_bytes(audio_data)

            return audio_data
        except Exception as e:
            logger.error(f"Edge-TTS failed: {e}")
            return b""

    async def synthesize_to_file(self, text: str) -> str:
        """Synthesize and return path to a temporary MP3 file."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            path = f.name
        await self.synthesize(text, output_path=path)
        return path

    async def stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """Yield audio chunks as they are generated."""
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"Edge-TTS stream failed: {e}")
