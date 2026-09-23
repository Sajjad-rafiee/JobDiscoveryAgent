import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    career_api_base_url: str
    openai_api_key: str


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        career_api_base_url=_require("CAREER_API_BASE_URL"),
        openai_api_key=_require("OPENAI_API_KEY"),
    )
