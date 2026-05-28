"""Embedding model abstraction for the retrieval pipeline.

Supports local inference via ``sentence-transformers`` (BGE-M3, nomic-embed-text)
and remote API calls (OpenAI, etc.). The factory ``create_embedder`` instantiates
the correct backend from ``EmbeddingConfig``.

Usage::

    from openhypothesis.config.schema import EmbeddingConfig
    from openhypothesis.tools.embedder import create_embedder

    config = EmbeddingConfig(model="BAAI/bge-m3", provider="sentence-transformers")
    embedder = create_embedder(config)
    vector = await embedder.embed("Gene expression in cancer cells")
    batch = await embedder.embed_batch(["text a", "text b", "text c"])
"""

import asyncio
import os
from abc import ABC, abstractmethod
from typing import Any

import httpx

from openhypothesis.config.schema import EmbeddingConfig

# Rough estimate: 4 chars per token for embedding models.
_CHARS_PER_TOKEN = 4


def _chunks(lst: list[str], size: int) -> list[list[str]]:
    """Yield successive chunks of ``size`` from the list."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]


class EmbeddingModel(ABC):
    """Abstract interface for text embedding models.

    Implementations handle batching internally and return normalized vectors
    as ``list[float]``.
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning one vector per input."""
        ...

    @abstractmethod
    def embed_sync(self, text: str) -> list[float]:
        """Synchronous single-text embedding (for use in non-async contexts)."""
        ...

    @abstractmethod
    def embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding."""
        ...


class _SentenceTransformerEmbedder(EmbeddingModel):
    """Local embedding via ``sentence-transformers``.

    Supports any model from Hugging Face (BGE-M3, nomic-embed-text, etc.).
    The model is loaded lazily on first ``embed`` call.
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model: Any = None

    def _ensure_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required for local embedding. "
                    "Install it with: uv sync --group local-embeddings"
                ) from exc
            self._model = SentenceTransformer(
                self._config.model,
                device=self._config.device,
            )
        return self._model

    async def embed(self, text: str) -> list[float]:
        model = self._ensure_model()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, model.encode, text)
        return list(result)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        results: list[list[float]] = []

        for batch in _chunks(texts, self._config.batch_size):
            loop = asyncio.get_running_loop()
            embeddings = await loop.run_in_executor(None, model.encode, batch)
            results.extend(list(e) for e in embeddings)

        return results

    def embed_sync(self, text: str) -> list[float]:
        model = self._ensure_model()
        return list(model.encode(text))

    def embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        model = self._ensure_model()
        results: list[list[float]] = []
        for batch in _chunks(texts, self._config.batch_size):
            embeddings = model.encode(batch)
            results.extend(list(e) for e in embeddings)
        return results


class _APIEmbedder(EmbeddingModel):
    """Remote API embedding via HTTP request.

    Supports OpenAI-compatible embedding APIs. The endpoint and model name
    are read from config; the API key is resolved from the environment.
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._api_model = config.api_model or config.model
        base_url = os.environ.get("EMBEDDING_API_BASE", self.DEFAULT_BASE_URL)
        api_key = ""
        if config.api_key_env:
            api_key = os.environ.get(config.api_key_env, "")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._url = f"{base_url.rstrip('/')}/embeddings"
        self._client = httpx.AsyncClient(timeout=60.0)
        self._sync_client = httpx.Client(timeout=60.0)

    async def embed(self, text: str) -> list[float]:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        all_results: list[list[float]] = []
        for batch in _chunks(texts, self._config.batch_size):
            payload = {
                "model": self._api_model,
                "input": batch,
            }
            response = await self._client.post(self._url, headers=self._headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # Sort by index to preserve order.
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            all_results.extend(item["embedding"] for item in sorted_data)
        return all_results

    def embed_sync(self, text: str) -> list[float]:
        results = self.embed_batch_sync([text])
        return results[0]

    def embed_batch_sync(self, texts: list[str]) -> list[list[float]]:
        all_results: list[list[float]] = []
        for batch in _chunks(texts, self._config.batch_size):
            payload = {
                "model": self._api_model,
                "input": batch,
            }
            response = self._sync_client.post(self._url, headers=self._headers, json=payload)
            response.raise_for_status()
            data = response.json()
            sorted_data = sorted(data["data"], key=lambda x: x["index"])
            all_results.extend(item["embedding"] for item in sorted_data)
        return all_results


def create_embedder(config: EmbeddingConfig) -> EmbeddingModel:
    """Factory: instantiate the correct embedder based on config.

    Args:
        config: Embedding configuration from ``AppConfig.embedding``.

    Returns:
        An ``EmbeddingModel`` instance ready for use.

    Raises:
        ValueError: If ``config.provider`` is not recognised.
    """
    provider = config.provider.lower()

    if provider == "sentence-transformers":
        return _SentenceTransformerEmbedder(config)
    if provider == "api":
        return _APIEmbedder(config)

    raise ValueError(
        f"Unknown embedding provider '{config.provider}'. "
        f"Expected 'sentence-transformers' or 'api'."
    )
