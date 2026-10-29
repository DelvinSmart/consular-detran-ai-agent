"""Pregunta al agente desde la terminal, sin levantar el servidor.

    python scripts/ask.py "¿Qué documentos necesito para canjear mi licencia?"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_core import RAGAgent, Settings  # noqa: E402
from agent_core.providers import build_provider  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Uso: python scripts/ask.py "tu pregunta"')
    settings = Settings.from_env()
    agent = RAGAgent.from_settings(settings, build_provider(settings))
    answer = agent.ask(" ".join(sys.argv[1:]))
    print(answer.answer)
    for s in answer.sources:
        page = f", pág. {s.page}" if s.page else ""
        print(f"  - {s.source}{page} (similitud {s.score})")


if __name__ == "__main__":
    main()
