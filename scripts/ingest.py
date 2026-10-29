"""Construye el índice vectorial a partir de `data/documents/`.

    python scripts/ingest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_core import Settings, build_index  # noqa: E402
from agent_core.providers import build_provider  # noqa: E402


def main() -> None:
    settings = Settings.from_env()
    provider = build_provider(settings)
    print(f"Indexando {settings.documents_dir} con {provider.name}/{provider.embedding_model}...")
    store = build_index(settings, provider)
    print(f"Listo: {len(store)} fragmentos guardados en {settings.index_path}")


if __name__ == "__main__":
    main()
