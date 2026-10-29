"""Dependencias compartidas por los canales: una sola instancia del agente
(el mismo cerebro) para todos.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from agent_core import RAGAgent, Settings
from agent_core.providers import build_provider


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache
def _build_agent() -> RAGAgent:
    settings = get_settings()
    return RAGAgent.from_settings(settings, build_provider(settings))


def get_agent() -> RAGAgent:
    try:
        return _build_agent()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        # lru_cache no guarda excepciones: el siguiente request lo reintenta.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
