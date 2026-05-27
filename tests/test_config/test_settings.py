from openhypothesis.config.schema import AppConfig, ModelProfile
from openhypothesis.config.settings import Settings


def test_settings_defaults() -> None:
    s = Settings()
    assert s.openai_api_key == ""
    assert s.ollama_api_base == "http://localhost:11434"


def test_settings_loads_env() -> None:
    import os
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    s = Settings()
    assert s.openai_api_key == "sk-test-key"
    del os.environ["OPENAI_API_KEY"]


def test_settings_app_config_defaults() -> None:
    s = Settings(config_path="nonexistent.yaml")
    cfg = s.app_config
    assert isinstance(cfg, AppConfig)
    assert cfg.models is None


def test_model_profile_defaults() -> None:
    p = ModelProfile(provider="openai", model="gpt-4o")
    assert p.temperature == 0.7
    assert p.max_tokens == 4096
    assert p.top_p == 0.95
    assert p.api_base is None


def test_resolve_api_key() -> None:
    import os
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    s = Settings()
    result = s.resolve_api_key("anthropic_api_key")
    assert result == "sk-ant-test"
    del os.environ["ANTHROPIC_API_KEY"]


def test_resolve_api_key_none() -> None:
    s = Settings()
    assert s.resolve_api_key(None) == ""
