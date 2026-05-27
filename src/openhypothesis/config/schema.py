from pydantic import BaseModel, Field


class ModelProfile(BaseModel):
    provider: str
    model: str
    api_base: str | None = None
    api_key_env: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95


class ModelConfig(BaseModel):
    exploration: ModelProfile
    adversarial: ModelProfile
    grounding: ModelProfile
    feasibility: ModelProfile
    meta_reasoning: ModelProfile


class RouterConfig(BaseModel):
    default_max_retries: int = 3
    retry_after: float = 5.0
    allowed_fails: int = 3
    cooldown_time: int = 60
    request_timeout: int = 120
    num_retries_on_timeout: int = 2
    fallback_strategy: str = "cascade"


class AppConfig(BaseModel):
    models: ModelConfig | None = None
    router: RouterConfig = Field(default_factory=lambda: RouterConfig())
