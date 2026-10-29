"""Ejecuta el bot de Telegram en modo polling (desarrollo local, sin HTTPS).

    python scripts/telegram_polling.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from channels.deps import get_settings  # noqa: E402
from channels.telegram import run_polling  # noqa: E402


def main() -> None:
    print("Bot de Telegram escuchando (Ctrl+C para salir)...")
    try:
        run_polling(get_settings())
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()
