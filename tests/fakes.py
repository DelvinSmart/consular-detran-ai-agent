"""Proveedor falso y determinístico para testear el núcleo sin API keys."""

from __future__ import annotations

import re

from agent_core.providers.base import LLMProvider

VOCABULARY = ["licencia", "canje", "carta", "consular", "consulado", "detran", "pasaporte", "pizza"]


class FakeProvider(LLMProvider):
    name = "fake"
    embedding_model = "bag-of-words"

    def __init__(self, reply: str = "Respuesta basada en el contexto [1].") -> None:
        self.reply = reply
        self.generate_calls = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            words = re.findall(r"\w+", text.lower())
            vectors.append([float(sum(w.startswith(v) for w in words)) for v in VOCABULARY])
        return vectors

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.generate_calls += 1
        return self.reply
