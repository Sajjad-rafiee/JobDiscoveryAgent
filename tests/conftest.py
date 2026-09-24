import pytest

from utils import config as config_module

CONFIG_ENV_VARS = (
    "CAREER_API_MODE",
    "CAREER_API_BASE_URL",
    "CAREER_API_SEARCH_PATH",
    "MODEL_PROVIDER",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
)


@pytest.fixture(autouse=True)
def isolated_config_env(monkeypatch):
    """Keep every test independent of the shell environment and any local `.env`.

    Without this, `load_dotenv()` would fill unset variables from a developer's
    `.env`, and exported shell variables would change test results.
    """
    monkeypatch.setattr(config_module, "load_dotenv", lambda *args, **kwargs: False)
    for name in CONFIG_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
