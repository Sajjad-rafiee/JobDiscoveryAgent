from utils.config import load_settings


def test_load_settings_reads_required_values(monkeypatch):
    monkeypatch.setenv("CAREER_API_BASE_URL", "http://test-api")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    settings = load_settings()

    assert settings.career_api_base_url == "http://test-api"
    assert settings.openai_api_key == "test-key"
