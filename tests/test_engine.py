import pytest

from agent_core.engine import RAGAgent
from agent_core.models import Chunk
from agent_core.prompts import NO_ANSWER
from agent_core.vector_store import VectorStore
from tests.fakes import FakeProvider


def _agent(provider: FakeProvider, min_similarity: float = 0.3) -> RAGAgent:
    chunks = [
        Chunk(id="1", source="guia.md", text="El canje de licencia extranjera se hace en el DETRAN."),
        Chunk(id="2", source="guia.md", text="La carta consular la emite el consulado con el pasaporte."),
    ]
    store = VectorStore(provider.name, provider.embedding_model)
    store.add(chunks, provider.embed([c.text for c in chunks]))
    return RAGAgent(provider, store, top_k=2, min_similarity=min_similarity)


def test_answers_with_sources_when_context_matches():
    provider = FakeProvider()
    answer = _agent(provider).ask("¿Dónde hago el canje de mi licencia?")
    assert answer.grounded
    assert answer.sources[0].excerpt.startswith("El canje")
    assert provider.generate_calls == 1


def test_declines_without_calling_llm_when_nothing_is_relevant():
    provider = FakeProvider()
    answer = _agent(provider).ask("¿Cuál es la mejor pizza de la ciudad?")
    assert not answer.grounded
    assert answer.answer == NO_ANSWER
    assert provider.generate_calls == 0


def test_model_refusal_is_marked_as_ungrounded():
    provider = FakeProvider(reply=NO_ANSWER)
    answer = _agent(provider).ask("¿La carta consular cuesta algo?")
    assert not answer.grounded
    assert answer.sources == []


def test_rejects_index_from_another_embedding_model():
    store = VectorStore("openai", "text-embedding-3-small")
    with pytest.raises(RuntimeError, match="ingest"):
        RAGAgent(FakeProvider(), store, top_k=2, min_similarity=0.3)


def test_vector_store_roundtrip(tmp_path):
    provider = FakeProvider()
    agent_store = VectorStore(provider.name, provider.embedding_model)
    agent_store.add([Chunk(id="1", source="a.md", text="licencia")], [[1.0, 0.0]])
    path = tmp_path / "index.json"
    agent_store.save(path)
    loaded = VectorStore.load(path)
    assert len(loaded) == 1
    assert loaded.embedding_model == "bag-of-words"
