"""Proveedor OpenAI — embeddings + chat completions."""

from __future__ import annotations

from openai import OpenAI

from agent_core.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, chat_model: str, embedding_model: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._chat_model = chat_model
        self.embedding_model = embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        completion = self._client.chat.completions.create(
            model=self._chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI devolvió una respuesta vacía.")
        return content.strip()
