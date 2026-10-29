"""Interfaz común de los proveedores de IA.

Cualquier proveedor nuevo (Claude, Mistral, un modelo local, etc.) solo
necesita implementar `embed()` y `generate()` para funcionar con el resto del
núcleo — el `RAGAgent` no sabe ni le importa qué proveedor está usando.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str
    embedding_model: str

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Devuelve un vector por cada texto, en el mismo orden."""
        raise NotImplementedError

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Genera una respuesta de texto. Debe lanzar una excepción si la
        llamada falla — nunca devolver texto inventado en silencio.
        """
        raise NotImplementedError
