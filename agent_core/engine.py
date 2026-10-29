"""Motor RAG: el "cerebro" único que consumen todos los canales.

Flujo de `ask()`:
  1. Embedding de la pregunta.
  2. Recuperación de los `top_k` fragmentos más similares.
  3. Barrera 1 — si ninguno supera `min_similarity`, se declina SIN llamar al
     modelo (no hay forma de que alucine si no se le pregunta).
  4. Barrera 2 — el modelo responde con un prompt de contexto estricto y
     temperatura 0; si devuelve la frase de "no sé", la respuesta se marca
     como no fundamentada y sin fuentes.
"""

from __future__ import annotations

from agent_core.config import Settings
from agent_core.ingestion import chunk_directory
from agent_core.models import Answer, Source
from agent_core.prompts import NO_ANSWER, SYSTEM_PROMPT, build_user_prompt
from agent_core.providers import LLMProvider
from agent_core.vector_store import VectorStore

EMBED_BATCH_SIZE = 64
MAX_QUESTION_CHARS = 1000


def build_index(settings: Settings, provider: LLMProvider) -> VectorStore:
    """Lee `documents_dir`, genera embeddings y guarda el índice en disco."""
    chunks = chunk_directory(settings.documents_dir, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise RuntimeError(f"No se encontraron documentos (.pdf/.txt/.md) en {settings.documents_dir}")

    store = VectorStore(provider.name, provider.embedding_model)
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        store.add(batch, provider.embed([c.text for c in batch]))
    store.save(settings.index_path)
    return store


class RAGAgent:
    def __init__(self, provider: LLMProvider, store: VectorStore, top_k: int, min_similarity: float):
        if (store.provider, store.embedding_model) != (provider.name, provider.embedding_model):
            raise RuntimeError(
                f"El índice se creó con {store.provider}/{store.embedding_model} pero el proveedor "
                f"actual es {provider.name}/{provider.embedding_model}. Vuelve a ejecutar scripts/ingest.py."
            )
        self._provider = provider
        self._store = store
        self._top_k = top_k
        self._min_similarity = min_similarity

    @classmethod
    def from_settings(cls, settings: Settings, provider: LLMProvider) -> "RAGAgent":
        store = VectorStore.load(settings.index_path)
        return cls(provider, store, settings.top_k, settings.min_similarity)

    def ask(self, question: str) -> Answer:
        question = question.strip()[:MAX_QUESTION_CHARS]
        if not question:
            return Answer(answer="Escribe tu pregunta, por favor.", grounded=False)

        query_vector = self._provider.embed([question])[0]
        hits = [
            (chunk, score)
            for chunk, score in self._store.search(query_vector, self._top_k)
            if score >= self._min_similarity
        ]
        if not hits:
            return Answer(answer=NO_ANSWER, grounded=False)

        user_prompt = build_user_prompt(
            question,
            [f"(Fuente: {c.source}{f', pág. {c.page}' if c.page else ''})\n{c.text}" for c, _ in hits],
        )
        text = self._provider.generate(SYSTEM_PROMPT, user_prompt)

        if NO_ANSWER[:40] in text:
            return Answer(answer=NO_ANSWER, grounded=False)

        return Answer(
            answer=text,
            grounded=True,
            sources=[
                Source(source=c.source, page=c.page, score=round(s, 3), excerpt=c.text[:240])
                for c, s in hits
            ],
        )
