from functools import lru_cache

from langchain_openai import ChatOpenAI

from tools.job_search import search_jobs
from utils.config import load_settings


@lru_cache
def get_chat_model() -> ChatOpenAI:
    settings = load_settings()
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)


@lru_cache
def get_tool_enabled_chat_model():
    return get_chat_model().bind_tools([search_jobs])
