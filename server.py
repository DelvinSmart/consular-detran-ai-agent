"""Punto de entrada HTTP. Solo ensambla canales — no contiene lógica de IA.

    Local:       uvicorn server:app --reload
    Producción:  uvicorn server:app --host 0.0.0.0 --port $PORT
                 (o el Dockerfile, que hace exactamente eso)

Toda la configuración llega por variables de entorno. `.env` solo se usa en
local: en la nube se definen en el panel de la plataforma, y `load_dotenv()`
nunca pisa una variable que ya exista en el entorno.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from agent_core import build_index
from agent_core.providers import build_provider
from channels import telegram, web, whatsapp
from channels.deps import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("server")


def _auto_ingest() -> None:
    """En la nube el disco suele ser efímero y el índice no viaja en git:
    si falta y hay documentos, se construye al arrancar.
    """
    settings = get_settings()
    if not settings.auto_ingest or settings.index_path.exists():
        return
    try:
        store = build_index(settings, build_provider(settings))
        logger.info("Auto-ingest: %d fragmentos indexados.", len(store))
    except Exception as exc:  # noqa: BLE001 — el servidor arranca igual; /health lo reporta
        logger.error("Auto-ingest falló: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _auto_ingest()
    yield


app = FastAPI(
    title="Consular & DETRAN AI Agent",
    description="Agente RAG headless tri-canal: Panel Web, WhatsApp y Telegram.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(web.router)
app.include_router(whatsapp.router)
app.include_router(telegram.router)


@app.get("/health", tags=["infra"])
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "provider": settings.provider,
        "index_ready": settings.index_path.exists(),
        "channels": {
            "web": True,
            "whatsapp": settings.whatsapp_enabled,
            "telegram": settings.telegram_enabled,
        },
    }


# Panel de chat de pruebas. Se monta al final para no tapar las rutas de la API.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="web")
