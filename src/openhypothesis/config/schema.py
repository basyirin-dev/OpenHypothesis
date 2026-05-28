from enum import StrEnum

from pydantic import BaseModel, Field


class FallbackStrategy(StrEnum):
    """How the ModelRouter selects fallback models when the primary fails.

    - CASCADE: try models in order, stop at first success.
    - ROUND_ROBIN: cycle through models. (Not yet implemented.)
    """

    CASCADE = "cascade"
    ROUND_ROBIN = "round_robin"


class ModelProfile(BaseModel):
    """Configuration for a single model used by one agent pool.

    ``api_key_env`` references the environment variable name (e.g. ``"OPENAI_API_KEY"``)
    that holds the secret; it is resolved at runtime by ``Settings.resolve_api_key``.
    """

    provider: str
    model: str
    api_base: str | None = None
    api_key_env: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95


class ModelConfig(BaseModel):
    """Per-pool model profile assignments. Each agent pool gets its own profile."""

    exploration: ModelProfile
    adversarial: ModelProfile
    grounding: ModelProfile
    feasibility: ModelProfile
    meta_reasoning: ModelProfile


class RouterConfig(BaseModel):
    """Global LiteLLM router settings shared across all agent pools."""

    default_max_retries: int = 3
    retry_after: float = 5.0
    allowed_fails: int = 3
    cooldown_time: int = 60
    request_timeout: int = 120
    num_retries_on_timeout: int = 2
    fallback_strategy: FallbackStrategy = FallbackStrategy.CASCADE


class EmbeddingConfig(BaseModel):
    """Configuration for the embedding model used in the retrieval pipeline.

    ``provider`` is either ``"sentence-transformers"`` (local inference via
    ``sentence-transformers``) or ``"api"`` (remote API like OpenAI embeddings).
    When using the API provider, ``api_key_env`` and ``api_model`` specify the
    credential and model name respectively.
    """

    model: str = "BAAI/bge-m3"
    provider: str = "sentence-transformers"
    dimension: int = 1024
    device: str = "cpu"
    batch_size: int = 32
    api_key_env: str | None = None
    api_model: str | None = None


class HNSWConfig(BaseModel):
    """HNSW index parameters for Qdrant collections.

    Values are tuned for high-dimensional (768-1024) scientific text embeddings.
    Higher ``ef_construct`` and ``ef_search`` improve recall at the cost of
    index/build time and query latency.
    """

    m: int = 16
    ef_construct: int = 200
    ef_search: int = 256


class QdrantConfig(BaseModel):
    """Connection and collection settings for the Qdrant vector database.

    ``host`` / ``port`` / ``grpc_port`` control the network endpoint.
    ``collection`` is the default collection name for scientific paper chunks.
    """

    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    collection: str = "scientific_papers"
    hnsw: HNSWConfig = Field(default_factory=HNSWConfig)


class AppConfig(BaseModel):
    """Top-level application config wrapping model profiles, router settings,
    embedding configuration, and Qdrant connection parameters.

    Loaded from ``config.yaml``; if the file is absent, default values are used
    for all sections, and each agent pool falls back to automatic model selection.
    """

    models: ModelConfig | None = None
    router: RouterConfig = Field(default_factory=lambda: RouterConfig())
    embedding: EmbeddingConfig = Field(default_factory=lambda: EmbeddingConfig())
    qdrant: QdrantConfig = Field(default_factory=lambda: QdrantConfig())
