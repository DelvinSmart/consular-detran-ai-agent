import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from agent_core.models import Answer
from channels import whatsapp
from channels.deps import get_agent
from server import app


class StubAgent:
    def ask(self, question: str) -> Answer:
        return Answer(answer=f"eco: {question}", grounded=True)


app.dependency_overrides[get_agent] = lambda: StubAgent()
client = TestClient(app)


def test_web_chat_returns_agent_answer():
    response = client.post("/api/chat", json={"message": "hola"})
    assert response.status_code == 200
    assert response.json()["answer"] == "eco: hola"


def test_web_panel_is_served():
    assert "Asistente DETRAN" in client.get("/").text


def test_whatsapp_disabled_by_default(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENABLED", "false")
    whatsapp.get_settings.cache_clear()
    params = {"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "1"}
    assert client.get("/webhooks/whatsapp", params=params).status_code == 404


def test_whatsapp_rejects_bad_signature(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENABLED", "true")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "secreto")
    whatsapp.get_settings.cache_clear()
    response = client.post(
        "/webhooks/whatsapp", content=b"{}", headers={"X-Hub-Signature-256": "sha256=malo"}
    )
    assert response.status_code == 401
    whatsapp.get_settings.cache_clear()


def test_whatsapp_verify_and_receive(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENABLED", "true")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "mi-token")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "secreto")
    whatsapp.get_settings.cache_clear()
    monkeypatch.setattr(whatsapp, "get_agent", lambda: StubAgent())
    sent = []
    monkeypatch.setattr(whatsapp, "send_text", lambda settings, to, text: sent.append((to, text)))

    params = {"hub.mode": "subscribe", "hub.verify_token": "mi-token", "hub.challenge": "42"}
    assert client.get("/webhooks/whatsapp", params=params).text == "42"

    body = json.dumps({
        "entry": [{"changes": [{"value": {"messages": [
            {"from": "5592999999999", "type": "text", "text": {"body": "licencia"}}
        ]}}]}]
    }).encode()
    signature = "sha256=" + hmac.new(b"secreto", body, hashlib.sha256).hexdigest()
    response = client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": signature, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert sent == [("5592999999999", "eco: licencia")]
    whatsapp.get_settings.cache_clear()
