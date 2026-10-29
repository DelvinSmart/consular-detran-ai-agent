"""Ingesta de documentos de referencia: lectura de PDF/TXT/MD y división en
fragmentos (chunks) con solapamiento, listos para generar embeddings.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from agent_core.models import Chunk

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def load_document(path: Path) -> list[tuple[int | None, str]]:
    """Devuelve una lista de (página, texto). Para TXT/MD la página es None."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return [(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]
    if suffix in {".txt", ".md"}:
        return [(None, path.read_text(encoding="utf-8"))]
    raise ValueError(f"Formato no soportado: {path.name}")


def normalize(text: str) -> str:
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Divide por párrafos y los agrupa hasta `chunk_size` caracteres. Los
    párrafos más largos que `chunk_size` se cortan con una ventana deslizante.
    Cada chunk nuevo arranca con los últimos `overlap` caracteres del anterior
    para no perder contexto en los bordes.
    """
    if overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP debe ser menor que CHUNK_SIZE.")

    pieces: list[str] = []
    for paragraph in (p.strip() for p in text.split("\n\n")):
        if not paragraph:
            continue
        if len(paragraph) <= chunk_size:
            pieces.append(paragraph)
            continue
        step = chunk_size - overlap
        pieces.extend(paragraph[i : i + chunk_size] for i in range(0, len(paragraph), step))

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{piece}" if tail and len(tail) + len(piece) + 2 <= chunk_size else piece
        else:
            current = piece
    if current:
        chunks.append(current)
    return chunks


def chunk_directory(directory: Path, chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(directory.rglob("*")):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS or path.name.lower() == "readme.md":
            continue
        for page, raw in load_document(path):
            for text in split_text(normalize(raw), chunk_size, overlap):
                digest = hashlib.sha1(f"{path.name}:{page}:{text}".encode()).hexdigest()[:12]
                chunks.append(Chunk(id=digest, source=path.name, page=page, text=text))
    return chunks
