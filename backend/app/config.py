"""
Central configuration for the Voice Agent.
Loads from environment variables / .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    groq_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.groq.com/openai/v1"
    llm_provider: Literal["groq", "openai"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"

    # STT
    assemblyai_api_key: str = ""
    deepgram_api_key: str = ""
    stt_provider: Literal["assemblyai", "deepgram", "faster-whisper"] = "assemblyai"

    # TTS
    tts_provider: Literal["edge", "browser", "piper"] = "edge"
    tts_voice: str = "en-US-AriaNeural"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 7860
    debug: bool = True

    # Paths
    documents_dir: Path = Path("./data/documents")
    vector_store_dir: Path = Path("./data/vector_store")

    def ensure_dirs(self) -> None:
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
