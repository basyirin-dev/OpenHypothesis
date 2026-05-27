from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

from openhypothesis.config.schema import AppConfig


class Settings(BaseSettings):
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
        if self._app_config is None:
            path = Path(self.config_path)
            if path.exists():
                raw = yaml.safe_load(path.read_text())
                self._app_config = AppConfig(**raw)
            else:
                self._app_config = AppConfig()
        return self._app_config

    def resolve_api_key(self, profile_api_key_env: str | None) -> str:
        if profile_api_key_env is None:
            return ""
        return getattr(self, profile_api_key_env.lower(), "")
