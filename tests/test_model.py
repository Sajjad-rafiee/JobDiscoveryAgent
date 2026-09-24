import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from agent import model as model_module
from agent.model import get_chat_model, get_tool_enabled_chat_model
from tools import TOOLS
from utils.config import CareerAPISettings, Settings


@pytest.fixture(autouse=True)
def _clear_model_cache():
    # get_chat_model/get_tool_enabled_chat_model are lru_cache'd across the
    # whole test process; without clearing, the first test's provider choice
    # would leak into every later test.
    get_chat_model.cache_clear()
    get_tool_enabled_chat_model.cache_clear()
    yield
    get_chat_model.cache_clear()
    get_tool_enabled_chat_model.cache_clear()


def _set_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-gemini-model")


def _set_openai_env(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")


def test_gemini_provider_builds_chat_google_generative_ai(monkeypatch):
    _set_gemini_env(monkeypatch)

    model = get_chat_model()

    assert isinstance(model, ChatGoogleGenerativeAI)
    assert model.model == "test-gemini-model"


def test_openai_provider_builds_chat_openai(monkeypatch):
    _set_openai_env(monkeypatch)

    model = get_chat_model()

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "test-model"


def test_gemini_model_is_bound_to_shared_tools(monkeypatch):
    _set_gemini_env(monkeypatch)

    tool_model = get_tool_enabled_chat_model()

    assert isinstance(tool_model.bound, ChatGoogleGenerativeAI)
    assert len(tool_model.kwargs["tools"]) == len(TOOLS)


def test_openai_model_is_bound_to_shared_tools(monkeypatch):
    _set_openai_env(monkeypatch)

    tool_model = get_tool_enabled_chat_model()

    assert isinstance(tool_model.bound, ChatOpenAI)
    assert len(tool_model.kwargs["tools"]) == len(TOOLS)


def test_get_chat_model_is_cached_per_process(monkeypatch):
    _set_gemini_env(monkeypatch)

    assert get_chat_model() is get_chat_model()


def test_build_chat_model_dispatches_on_provider():
    gemini_settings = Settings(
        model_provider="gemini",
        openai_api_key=None,
        openai_model=None,
        gemini_api_key="k",
        gemini_model="m",
        career_api=CareerAPISettings(mode="demo"),
    )
    openai_settings = Settings(
        model_provider="openai",
        openai_api_key="k",
        openai_model="m",
        gemini_api_key=None,
        gemini_model=None,
        career_api=CareerAPISettings(mode="demo"),
    )

    assert isinstance(model_module._build_chat_model(gemini_settings), ChatGoogleGenerativeAI)
    assert isinstance(model_module._build_chat_model(openai_settings), ChatOpenAI)
