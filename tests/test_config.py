import pytest

from utils.config import ConfigError, load_career_api_settings, load_settings


def _set_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-gemini-model")


def _set_openai_env(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")


def test_model_provider_defaults_to_gemini(monkeypatch):
    _set_gemini_env(monkeypatch)

    settings = load_settings()

    assert settings.model_provider == "gemini"


def test_gemini_config_requires_gemini_key_not_openai(monkeypatch):
    _set_gemini_env(monkeypatch)

    settings = load_settings()

    assert settings.gemini_api_key == "test-gemini-key"
    assert settings.gemini_model == "test-gemini-model"
    assert settings.openai_api_key is None
    assert settings.openai_model is None


@pytest.mark.parametrize("missing", ["GEMINI_API_KEY", "GEMINI_MODEL"])
def test_gemini_config_requires_its_own_values(monkeypatch, missing):
    _set_gemini_env(monkeypatch)
    monkeypatch.delenv(missing)

    with pytest.raises(ConfigError, match=missing):
        load_settings()


def test_openai_config_requires_openai_key_not_gemini(monkeypatch):
    _set_openai_env(monkeypatch)

    settings = load_settings()

    assert settings.model_provider == "openai"
    assert settings.openai_api_key == "test-key"
    assert settings.openai_model == "test-model"
    assert settings.gemini_api_key is None
    assert settings.gemini_model is None


@pytest.mark.parametrize("missing", ["OPENAI_API_KEY", "OPENAI_MODEL"])
def test_openai_config_requires_its_own_values(monkeypatch, missing):
    _set_openai_env(monkeypatch)
    monkeypatch.delenv(missing)

    with pytest.raises(ConfigError, match=missing):
        load_settings()


def test_invalid_model_provider_raises_config_error(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "anthropic")

    with pytest.raises(ConfigError, match="Unsupported MODEL_PROVIDER: 'anthropic'"):
        load_settings()


def test_career_api_mode_defaults_to_demo():
    settings = load_career_api_settings()

    assert settings.mode == "demo"
    assert settings.base_url is None
    assert settings.search_path is None


def test_demo_mode_does_not_require_base_url(monkeypatch):
    _set_gemini_env(monkeypatch)
    monkeypatch.setenv("CAREER_API_MODE", "demo")

    settings = load_settings()

    assert settings.career_api.mode == "demo"
    assert settings.career_api.base_url is None


def test_career_api_settings_do_not_require_model_provider_values(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "demo")

    assert load_career_api_settings().mode == "demo"


def test_http_mode_reads_required_values(monkeypatch):
    _set_gemini_env(monkeypatch)
    monkeypatch.setenv("CAREER_API_MODE", "http")
    monkeypatch.setenv("CAREER_API_BASE_URL", "http://test-api")
    monkeypatch.setenv("CAREER_API_SEARCH_PATH", "/opportunities/search")

    settings = load_settings()

    assert settings.career_api.mode == "http"
    assert settings.career_api.base_url == "http://test-api"
    assert settings.career_api.search_path == "/opportunities/search"


@pytest.mark.parametrize("missing", ["CAREER_API_BASE_URL", "CAREER_API_SEARCH_PATH"])
def test_http_mode_requires_base_url_and_search_path(monkeypatch, missing):
    monkeypatch.setenv("CAREER_API_MODE", "http")
    monkeypatch.setenv("CAREER_API_BASE_URL", "http://test-api")
    monkeypatch.setenv("CAREER_API_SEARCH_PATH", "/opportunities/search")
    monkeypatch.delenv(missing)

    with pytest.raises(ConfigError, match=missing):
        load_career_api_settings()


def test_http_mode_rejects_empty_required_value(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "http")
    monkeypatch.setenv("CAREER_API_BASE_URL", "")
    monkeypatch.setenv("CAREER_API_SEARCH_PATH", "/opportunities/search")

    with pytest.raises(ConfigError, match="CAREER_API_BASE_URL"):
        load_career_api_settings()


def test_invalid_career_api_mode_raises_config_error(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "production")

    with pytest.raises(ConfigError, match="Unsupported CAREER_API_MODE: 'production'"):
        load_career_api_settings()
