import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


CareerAPIMode = Literal["demo", "http"]

CAREER_API_MODES: tuple[CareerAPIMode, ...] = ("demo", "http")
DEFAULT_CAREER_API_MODE: CareerAPIMode = "demo"

ModelProvider = Literal["gemini", "openai"]

MODEL_PROVIDERS: tuple[ModelProvider, ...] = ("gemini", "openai")
DEFAULT_MODEL_PROVIDER: ModelProvider = "gemini"


@dataclass(frozen=True)
class CareerAPISettings:
    mode: CareerAPIMode
    base_url: str | None = None
    search_path: str | None = None


@dataclass(frozen=True)
class Settings:
    model_provider: ModelProvider
    openai_api_key: str | None
    openai_model: str | None
    gemini_api_key: str | None
    gemini_model: str | None
    career_api: CareerAPISettings


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _optional(name: str) -> str | None:
    return os.environ.get(name) or None


def _model_provider() -> ModelProvider:
    raw_provider = os.environ.get("MODEL_PROVIDER", "").strip().lower()
    if not raw_provider:
        return DEFAULT_MODEL_PROVIDER

    for provider in MODEL_PROVIDERS:
        if raw_provider == provider:
            return provider

    raise ConfigError(
        f"Unsupported MODEL_PROVIDER: {raw_provider!r} "
        f"(expected one of: {', '.join(MODEL_PROVIDERS)})"
    )


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
    provider = _model_provider()

    if provider == "gemini":
        gemini_api_key = _require("GEMINI_API_KEY")
        gemini_model = _require("GEMINI_MODEL")
        openai_api_key = _optional("OPENAI_API_KEY")
        openai_model = _optional("OPENAI_MODEL")
    else:
        openai_api_key = _require("OPENAI_API_KEY")
        openai_model = _require("OPENAI_MODEL")
        gemini_api_key = _optional("GEMINI_API_KEY")
        gemini_model = _optional("GEMINI_MODEL")

    return Settings(
        model_provider=provider,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        career_api=load_career_api_settings(),
    )
