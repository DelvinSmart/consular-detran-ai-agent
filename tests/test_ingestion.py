import pytest

from agent_core.ingestion import chunk_directory, split_text


def test_split_respects_chunk_size():
    text = "\n\n".join(f"Párrafo {i} " + "x" * 120 for i in range(20))
    chunks = split_text(text, chunk_size=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 400 for c in chunks)


def test_long_paragraph_is_windowed():
    chunks = split_text("a" * 1000, chunk_size=300, overlap=50)
    assert all(len(c) <= 300 for c in chunks)
    assert len(chunks) >= 4


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        split_text("hola", chunk_size=100, overlap=100)


def test_chunk_directory_skips_readme(tmp_path):
    (tmp_path / "README.md").write_text("instrucciones", encoding="utf-8")
    (tmp_path / "guia.md").write_text("Canje de licencia.\n\nCarta consular.", encoding="utf-8")
    (tmp_path / "foto.jpg").write_bytes(b"\xff")
    chunks = chunk_directory(tmp_path, chunk_size=500, overlap=50)
    assert {c.source for c in chunks} == {"guia.md"}
