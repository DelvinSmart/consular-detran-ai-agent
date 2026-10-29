"""Contratos de datos del núcleo. Los canales (web, WhatsApp, ...) solo
conocen estos modelos — nunca los detalles internos del motor RAG.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """Fragmento de un documento de referencia, listo para indexar."""

    id: str
    source: str = Field(description="Nombre del archivo de origen.")
    page: int | None = Field(default=None, description="Página (solo PDFs).")
    text: str


class Source(BaseModel):
    """Fragmento citado como respaldo de una respuesta."""

    source: str
    page: int | None = None
    score: float = Field(description="Similitud coseno con la pregunta (0–1).")
    excerpt: str


class Answer(BaseModel):
    """Respuesta del agente, independiente del canal que la muestre."""

    answer: str
    grounded: bool = Field(
        description="True si la respuesta se apoya en los documentos; "
        "False si el agente declinó por falta de contexto."
    )
    sources: list[Source] = Field(default_factory=list)
