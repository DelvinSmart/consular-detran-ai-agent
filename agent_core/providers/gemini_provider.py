"""Proveedor Gemini — embeddings + generate_content (SDK google-genai)."""

from __future__ import annotations

from google import genai
from google.genai import types

from agent_core.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, chat_model: str, embedding_model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._chat_model = chat_model
        self.embedding_model = embedding_model

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.models.embed_content(model=self.embedding_model, contents=texts)
        return [list(e.values) for e in result.embeddings]

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.models.generate_content(
            model=self._chat_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0,
            ),
        )
        if not response.text:
            raise RuntimeError("Gemini devolvió una respuesta vacía.")
        return response.text.strip()
