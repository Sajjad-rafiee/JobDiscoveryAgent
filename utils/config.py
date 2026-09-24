import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


CareerAPIMode = Literal["demo", "http"]

CAREER_API_MODES: tuple[CareerAPIMode, ...] = ("demo", "http")
DEFAULT_CAREER_API_MODE: CareerAPIMode = "demo"


@dataclass(frozen=True)
class CareerAPISettings:
    mode: CareerAPIMode
    base_url: str | None = None
    search_path: str | None = None


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    career_api: CareerAPISettings


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str) -> str | None:
    return os.environ.get(name) or None


def _career_api_mode() -> CareerAPIMode:
    raw_mode = os.environ.get("CAREER_API_MODE", "").strip().lower()
    if not raw_mode:
        return DEFAULT_CAREER_API_MODE

    for mode in CAREER_API_MODES:
        if raw_mode == mode:
            return mode

    raise ConfigError(
        f"Unsupported CAREER_API_MODE: {raw_mode!r} "
        f"(expected one of: {', '.join(CAREER_API_MODES)})"
    )


def load_career_api_settings() -> CareerAPISettings:
    load_dotenv()
    mode = _career_api_mode()

    if mode == "http":
        return CareerAPISettings(
            mode=mode,
            base_url=_require("CAREER_API_BASE_URL"),
            search_path=_require("CAREER_API_SEARCH_PATH"),
        )

    return CareerAPISettings(
        mode=mode,
        base_url=_optional("CAREER_API_BASE_URL"),
        search_path=_optional("CAREER_API_SEARCH_PATH"),
    )


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        openai_api_key=_require("OPENAI_API_KEY"),
        openai_model=_require("OPENAI_MODEL"),
        career_api=load_career_api_settings(),
    )
