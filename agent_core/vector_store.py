"""Índice vectorial local en un archivo JSON, con búsqueda por similitud
coseno en Python puro.

Suficiente para cientos/miles de fragmentos (el volumen típico de guías de
DETRAN y consulados). La interfaz `add / search / save / load` está pensada
para reemplazarse por Chroma, pgvector o Qdrant sin tocar el motor.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from agent_core.models import Chunk


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class VectorStore:
    def __init__(self, provider: str, embedding_model: str) -> None:
        # Se guarda qué modelo generó los vectores: mezclar embeddings de
        # modelos distintos produce similitudes sin sentido.
        self.provider = provider
        self.embedding_model = embedding_model
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Cada chunk necesita exactamente un vector.")
        self._chunks.extend(chunks)
        self._vectors.extend(vectors)

    def search(self, query_vector: list[float], top_k: int) -> list[tuple[Chunk, float]]:
        scored = [
            (chunk, cosine_similarity(query_vector, vector))
            for chunk, vector in zip(self._chunks, self._vectors)
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "provider": self.provider,
            "embedding_model": self.embedding_model,
            "items": [
                {"chunk": c.model_dump(), "vector": v} for c, v in zip(self._chunks, self._vectors)
            ],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "VectorStore":
        if not path.exists():
            raise FileNotFoundError(
                f"No existe el índice {path}. Ejecuta primero: python scripts/ingest.py"
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        store = cls(payload["provider"], payload["embedding_model"])
        store.add(
            [Chunk.model_validate(item["chunk"]) for item in payload["items"]],
            [item["vector"] for item in payload["items"]],
        )
        return store
