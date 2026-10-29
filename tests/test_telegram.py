from fastapi.testclient import TestClient

from agent_core.models import Answer, Source
from channels import telegram
from server import app

client = TestClient(app)


class StubAgent:
    def ask(self, question: str) -> Answer:
        return Answer(
            answer=f"eco: {question}",
            grounded=True,
            sources=[Source(source="guia.md", score=0.9, excerpt="...")],
        )


def _update(text: str) -> dict:
    return {"update_id": 1, "message": {"message_id": 7, "chat": {"id": 123}, "text": text}}


def _enable(monkeypatch, sent: list) -> None:
    monkeypatch.setenv("TELEGRAM_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "secreto")
    telegram.get_settings.cache_clear()
    monkeypatch.setattr(telegram, "get_agent", lambda: StubAgent())
    monkeypatch.setattr(
        telegram, "send_text", lambda settings, chat_id, text, reply_to=None: sent.append((chat_id, text))
    )


def test_telegram_disabled_by_default(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ENABLED", "false")
    telegram.get_settings.cache_clear()
    assert client.post("/webhooks/telegram", json=_update("hola")).status_code == 404


def test_telegram_rejects_bad_secret(monkeypatch):
    _enable(monkeypatch, [])
    response = client.post(
        "/webhooks/telegram", json=_update("hola"), headers={"X-Telegram-Bot-Api-Secret-Token": "malo"}
    )
    assert response.status_code == 401
    telegram.get_settings.cache_clear()


def test_telegram_answers_with_sources(monkeypatch):
    sent = []
    _enable(monkeypatch, sent)
    response = client.post(
        "/webhooks/telegram",
        json=_update("licencia"),
        headers={"X-Telegram-Bot-Api-Secret-Token": "secreto"},
    )
    assert response.status_code == 200
    assert sent == [(123, "eco: licencia\n\n📄 Fuentes: guia.md")]
    telegram.get_settings.cache_clear()


def test_start_command_sends_welcome_without_calling_agent(monkeypatch):
    sent = []
    _enable(monkeypatch, sent)
    monkeypatch.setattr(telegram, "get_agent", lambda: (_ for _ in ()).throw(AssertionError))
    telegram.handle_update(telegram.get_settings(), _update("/start"))
    assert sent == [(123, telegram.WELCOME)]
    telegram.get_settings.cache_clear()


def test_non_text_updates_are_ignored(monkeypatch):
    sent = []
    _enable(monkeypatch, sent)
    telegram.handle_update(telegram.get_settings(), {"update_id": 2, "message": {"photo": []}})
    assert sent == []
    telegram.get_settings.cache_clear()
