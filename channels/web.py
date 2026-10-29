"""Canal web: API JSON que consume el panel de chat de `web/`."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agent_core import Answer, RAGAgent
from channels.deps import get_agent

router = APIRouter(prefix="/api", tags=["web"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


@router.post("/chat", response_model=Answer)
def chat(request: ChatRequest, agent: RAGAgent = Depends(get_agent)) -> Answer:
    return agent.ask(request.message)
