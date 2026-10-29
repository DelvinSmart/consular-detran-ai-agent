"""Canal Telegram (Bot API) — adaptador PREPARADO.

Está desactivado por defecto (TELEGRAM_ENABLED=false): la ruta del webhook
existe pero responde 404 hasta configurarlo. Dos formas de usarlo:

  • Polling (desarrollo local, sin HTTPS):
        python scripts/telegram_polling.py

  • Webhook (producción):
      1. Crear el bot con @BotFather y copiar el token a TELEGRAM_BOT_TOKEN.
      2. Inventar TELEGRAM_WEBHOOK_SECRET (A-Z, a-z, 0-9, _ y -) y poner
         TELEGRAM_ENABLED=true en `.env`.
      3. Registrar el webhook una sola vez:
            curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \\
              -d url=https://<dominio>/webhooks/telegram \\
              -d secret_token=<TELEGRAM_WEBHOOK_SECRET>

Se habla con la Bot API directamente por HTTP (httpx), sin SDK extra. Este
módulo solo traduce mensajes de Telegram <-> `RAGAgent.ask()`; toda la
inteligencia vive en `agent_core`, igual que para el panel web y WhatsApp.
"""

from __future__ import annotations

import hmac
import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from agent_core import Settings
from channels.deps import get_agent, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/telegram", tags=["telegram"])

TELEGRAM_MAX_CHARS = 4096
POLL_TIMEOUT_SECONDS = 30

WELCOME = (
    "¡Hola! Soy un asistente sobre trámites de DETRAN, licencias de conducir "
    "y cartas consulares. Escríbeme tu pregunta.\n\n"
    "Respondo solo con base en documentos de referencia: confirma siempre con "
    "el DETRAN o el consulado oficial."
)


def _require_enabled() -> Settings:
    settings = get_settings()
    if not settings.telegram_enabled:
        raise HTTPException(status_code=404, detail="Canal Telegram desactivado.")
    return settings


@router.post("")
async def receive_update(request: Request, background: BackgroundTasks) -> dict:
    """Recibe updates de Telegram. Responde 200 de inmediato (Telegram
    reintenta si tarda) y procesa la pregunta en segundo plano.
    """
    settings = _require_enabled()
    if not settings.telegram_webhook_secret:
        raise HTTPException(status_code=500, detail="Falta TELEGRAM_WEBHOOK_SECRET.")
    header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(header, settings.telegram_webhook_secret):
        raise HTTPException(status_code=401, detail="Secret token inválido.")

    background.add_task(handle_update, settings, await request.json())
    return {"status": "received"}


def _extract_text_message(update: dict) -> tuple[int, int, str] | None:
    """Devuelve (chat_id, message_id, texto) si el update es un mensaje de
    texto. Ignora ediciones, fotos, stickers, etc.
    """
    message = update.get("message") or {}
    text = message.get("text")
    if not text:
        return None
    return message["chat"]["id"], message["message_id"], text


def handle_update(settings: Settings, update: dict) -> None:
    extracted = _extract_text_message(update)
    if extracted is None:
        return
    chat_id, message_id, text = extracted

    if text.startswith("/start") or text.startswith("/help"):
        send_text(settings, chat_id, WELCOME)
        return

    try:
        answer = get_agent().ask(text)
        reply = answer.answer
        if answer.sources:
            names = sorted({s.source for s in answer.sources})
            reply += "\n\n📄 Fuentes: " + ", ".join(names)
    except Exception:  # noqa: BLE001 — el usuario siempre debe recibir algo
        logger.exception("Error respondiendo mensaje de Telegram")
        reply = "Lo siento, tuve un problema técnico. Intenta de nuevo en unos minutos."
    send_text(settings, chat_id, reply[:TELEGRAM_MAX_CHARS], reply_to=message_id)


def _api_url(settings: Settings, method: str) -> str:
    return f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"


def send_text(settings: Settings, chat_id: int, text: str, reply_to: int | None = None) -> None:
    payload: dict = {"chat_id": chat_id, "text": text}
    if reply_to is not None:
        payload["reply_parameters"] = {"message_id": reply_to}
    response = httpx.post(_api_url(settings, "sendMessage"), json=payload, timeout=15)
    if response.is_error:
        # No se loguea la URL: contiene el token del bot.
        logger.error("Telegram API respondió %s: %s", response.status_code, response.text)


def run_polling(settings: Settings) -> None:
    """Bucle de long polling con getUpdates, para desarrollo local sin HTTPS.
    Telegram no permite polling mientras haya un webhook registrado, así que
    se elimina primero.
    """
    if not settings.telegram_bot_token:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en el .env.")
    httpx.post(_api_url(settings, "deleteWebhook"), timeout=15).raise_for_status()

    offset = 0
    with httpx.Client(timeout=POLL_TIMEOUT_SECONDS + 10) as client:
        while True:
            response = client.get(
                _api_url(settings, "getUpdates"),
                params={"offset": offset, "timeout": POLL_TIMEOUT_SECONDS, "allowed_updates": '["message"]'},
            )
            response.raise_for_status()
            for update in response.json().get("result", []):
                offset = update["update_id"] + 1
                handle_update(settings, update)
