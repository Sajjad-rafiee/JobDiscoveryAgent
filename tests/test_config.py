import pytest

from utils.config import ConfigError, load_career_api_settings, load_settings


def _set_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")


def test_load_settings_reads_openai_values(monkeypatch):
    _set_openai_env(monkeypatch)

    settings = load_settings()

    assert settings.openai_api_key == "test-key"
    assert settings.openai_model == "test-model"


@pytest.mark.parametrize("missing", ["OPENAI_API_KEY", "OPENAI_MODEL"])
def test_load_settings_requires_openai_values(monkeypatch, missing):
    _set_openai_env(monkeypatch)
    monkeypatch.delenv(missing)

    with pytest.raises(ConfigError, match=missing):
        load_settings()


def test_career_api_mode_defaults_to_demo():
    settings = load_career_api_settings()

    assert settings.mode == "demo"
    assert settings.base_url is None
    assert settings.search_path is None


def test_demo_mode_does_not_require_base_url(monkeypatch):
    _set_openai_env(monkeypatch)
    monkeypatch.setenv("CAREER_API_MODE", "demo")

    settings = load_settings()

    assert settings.career_api.mode == "demo"
    assert settings.career_api.base_url is None


def test_career_api_settings_do_not_require_openai_values(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "demo")

    assert load_career_api_settings().mode == "demo"


def test_http_mode_reads_required_values(monkeypatch):
    _set_openai_env(monkeypatch)
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


def test_invalid_mode_raises_config_error(monkeypatch):
    monkeypatch.setenv("CAREER_API_MODE", "production")

    with pytest.raises(ConfigError, match="Unsupported CAREER_API_MODE: 'production'"):
        load_career_api_settings()
