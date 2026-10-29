from agent_core.config import Settings
from agent_core.providers.base import LLMProvider

__all__ = ["LLMProvider", "build_provider"]


def build_provider(settings: Settings) -> LLMProvider:
    """Crea el proveedor configurado. Los imports son perezosos para que no
    haga falta instalar el SDK del proveedor que no se usa.
    """
    if settings.provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Falta OPENAI_API_KEY en el .env.")
        from agent_core.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(
            settings.openai_api_key, settings.openai_chat_model, settings.openai_embedding_model
        )

    if settings.provider == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("Falta GEMINI_API_KEY en el .env.")
        from agent_core.providers.gemini_provider import GeminiProvider

        return GeminiProvider(
            settings.gemini_api_key, settings.gemini_chat_model, settings.gemini_embedding_model
        )

    raise ValueError(f"AGENT_PROVIDER desconocido: {settings.provider!r} (usa 'openai' o 'gemini').")
