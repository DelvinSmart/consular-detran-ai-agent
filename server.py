"""Punto de entrada HTTP. Solo ensambla canales — no contiene lógica de IA.

    uvicorn server:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from channels import web, whatsapp

app = FastAPI(
    title="Consular & DETRAN AI Agent",
    description="Agente RAG headless: un cerebro, múltiples canales.",
    version="0.1.0",
)

app.include_router(web.router)
app.include_router(whatsapp.router)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok"}


# Panel de chat de pruebas. Se monta al final para no tapar las rutas de la API.
app.mount("/", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="web")
