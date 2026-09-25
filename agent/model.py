from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from tools import TOOLS
from utils.config import Settings, load_settings


def _build_chat_model(settings: Settings) -> ChatGoogleGenerativeAI | ChatOpenAI:
    if settings.model_provider == "gemini":
        return ChatGoogleGenerativeAI(model=settings.gemini_model, api_key=settings.gemini_api_key)
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)


@lru_cache
def get_chat_model() -> ChatGoogleGenerativeAI | ChatOpenAI:
    return _build_chat_model(load_settings())


@lru_cache
def get_tool_enabled_chat_model():
    return get_chat_model().bind_tools(TOOLS)


def get_model_info() -> tuple[str, str]:
    """Return (provider, model name) for telemetry attributes — never a key/prompt."""
    settings = load_settings()
    if settings.model_provider == "gemini":
        return "gemini", settings.gemini_model or ""
    return "openai", settings.openai_model or ""
