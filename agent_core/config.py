"""Configuración centralizada, leída SOLO desde variables de entorno.

Ningún secreto vive en el código: todo sale de `.env` (ignorado por git) o del
entorno del servidor donde se despliegue.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else PROJECT_ROOT / value


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    provider: str
    openai_api_key: str
    openai_chat_model: str
    openai_embedding_model: str
    gemini_api_key: str
    gemini_chat_model: str
    gemini_embedding_model: str

    documents_dir: Path
    index_path: Path
    chunk_size: int
    chunk_overlap: int
    top_k: int
    min_similarity: float
    auto_ingest: bool

    whatsapp_enabled: bool
    whatsapp_verify_token: str
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_app_secret: str
    whatsapp_api_version: str

    telegram_enabled: bool
    telegram_bot_token: str
    telegram_webhook_secret: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            provider=os.getenv("AGENT_PROVIDER", "openai").strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_chat_model=os.getenv("GEMINI_CHAT_MODEL", "gemini-3.8-flash"),
            gemini_embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
            documents_dir=_path("DOCUMENTS_DIR", "data/documents"),
            index_path=_path("INDEX_PATH", "data/index/index.json"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "900")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "150")),
            top_k=int(os.getenv("TOP_K", "4")),
            min_similarity=float(os.getenv("MIN_SIMILARITY", "0.35")),
            auto_ingest=_bool("AUTO_INGEST", True),
            whatsapp_enabled=_bool("WHATSAPP_ENABLED"),
            whatsapp_verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN", ""),
            whatsapp_access_token=os.getenv("WHATSAPP_ACCESS_TOKEN", ""),
            whatsapp_phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
            whatsapp_app_secret=os.getenv("WHATSAPP_APP_SECRET", ""),
            whatsapp_api_version=os.getenv("WHATSAPP_API_VERSION", "v21.0"),
            telegram_enabled=_bool("TELEGRAM_ENABLED"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
        )
