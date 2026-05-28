from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from openhypothesis.config.schema import AppConfig


class Settings(BaseSettings):
    """Combined settings from environment variables and an optional YAML config file.

    API keys are loaded from ``.env`` (via pydantic-settings) or the process
    environment. The field names here are the snake_case version of the standard
    env variable name (e.g. ``openai_api_key`` ← ``OPENAI_API_KEY``).

    ``resolve_api_key`` maps a ``ModelProfile.api_key_env`` value (e.g.
    ``"anthropic_api_key"``) to the corresponding field value at runtime.
    """

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    together_ai_api_key: str = ""
    deepseek_api_key: str = ""

    ollama_api_base: str = "http://localhost:11434"
    vllm_api_base: str = "http://localhost:8000/v1"
    llamacpp_api_base: str = "http://localhost:8080/v1"

    config_path: str = "config.yaml"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    _app_config: AppConfig | None = None

    @property
    def app_config(self) -> AppConfig:
        """Load and cache the YAML-based ``AppConfig``.

        If ``config.yaml`` is missing, returns a default ``AppConfig`` with no
        model profiles — each agent pool will use auto-selected models.
        """
        if self._app_config is None:
            path = Path(self.config_path)
            if path.exists():
                raw = yaml.safe_load(path.read_text())
                self._app_config = AppConfig(**raw)
            else:
                self._app_config = AppConfig()
        return self._app_config

    def resolve_api_key(self, profile_api_key_env: str | None) -> str:
        """Resolve a ``ModelProfile.api_key_env`` name to its actual key value.

        The input must match a field name on this class in lowercase
        (e.g. ``"anthropic_api_key"``).
        """
        if profile_api_key_env is None:
            return ""
        return getattr(self, profile_api_key_env.lower(), "")
