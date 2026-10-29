"""Canal WhatsApp Business (Cloud API de Meta) — adaptador PREPARADO.

Está desactivado por defecto (WHATSAPP_ENABLED=false): las rutas existen pero
responden 404 hasta que se configure la cuenta de Meta. Para activarlo:

  1. Crear una app en https://developers.facebook.com con el producto WhatsApp.
  2. Completar en `.env`: WHATSAPP_VERIFY_TOKEN, WHATSAPP_ACCESS_TOKEN,
     WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_APP_SECRET y WHATSAPP_ENABLED=true.
  3. Exponer el servidor con HTTPS (p. ej. `ngrok http 8000`) y registrar
     `https://<dominio>/webhooks/whatsapp` como Callback URL, suscribiendo el
     campo "messages".

Este módulo solo traduce mensajes de WhatsApp <-> `RAGAgent.ask()`; toda la
inteligencia vive en `agent_core`, igual que para el panel web.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response

from agent_core import Settings
from channels.deps import get_agent, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["whatsapp"])

WHATSAPP_MAX_CHARS = 4096


def _require_enabled() -> Settings:
    settings = get_settings()
    if not settings.whatsapp_enabled:
        raise HTTPException(status_code=404, detail="Canal WhatsApp desactivado.")
    return settings


@router.get("")
def verify_webhook(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge"),
) -> Response:
    """Handshake de verificación que Meta hace al registrar el webhook."""
    settings = _require_enabled()
    if mode == "subscribe" and settings.whatsapp_verify_token and hmac.compare_digest(
        token, settings.whatsapp_verify_token
    ):
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Token de verificación inválido.")


@router.post("")
async def receive_message(request: Request, background: BackgroundTasks) -> dict:
    """Recibe eventos de Meta. Responde 200 de inmediato (Meta reintenta si
    tarda) y procesa la pregunta en segundo plano.
    """
    settings = _require_enabled()
    body = await request.body()
    _verify_signature(body, request.headers.get("X-Hub-Signature-256", ""), settings.whatsapp_app_secret)

    payload = await request.json()
    for sender, text in _extract_text_messages(payload):
        background.add_task(_answer_and_reply, settings, sender, text)
    return {"status": "received"}


def _verify_signature(body: bytes, header: str, app_secret: str) -> None:
    if not app_secret:
        raise HTTPException(status_code=500, detail="Falta WHATSAPP_APP_SECRET.")
    expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, header):
        raise HTTPException(status_code=401, detail="Firma inválida.")


def _extract_text_messages(payload: dict) -> list[tuple[str, str]]:
    """Devuelve (número_remitente, texto) de cada mensaje de texto. Ignora
    estados de entrega, audios, imágenes, etc.
    """
    messages: list[tuple[str, str]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if message.get("type") == "text":
                    messages.append((message["from"], message["text"]["body"]))
    return messages


def _answer_and_reply(settings: Settings, to: str, question: str) -> None:
    try:
        answer = get_agent().ask(question)
        text = answer.answer
        if answer.sources:
            names = sorted({s.source for s in answer.sources})
            text += "\n\n📄 Fuentes: " + ", ".join(names)
    except Exception:  # noqa: BLE001 — el usuario siempre debe recibir algo
        logger.exception("Error respondiendo mensaje de WhatsApp")
        text = "Lo siento, tuve un problema técnico. Intenta de nuevo en unos minutos."
    send_text(settings, to, text[:WHATSAPP_MAX_CHARS])


def send_text(settings: Settings, to: str, text: str) -> None:
    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
        timeout=15,
    )
    if response.is_error:
        logger.error("WhatsApp API respondió %s: %s", response.status_code, response.text)
