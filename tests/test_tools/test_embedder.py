"""Tests for the EmbeddingModel factory and implementations."""

import pytest

from openhypothesis.config.schema import EmbeddingConfig
from openhypothesis.tools.embedder import _APIEmbedder, _SentenceTransformerEmbedder, create_embedder


class TestCreateEmbedder:
    """Factory dispatch logic."""

    def test_creates_sentence_transformer_embedder(self) -> None:
        """sentence-transformers provider returns the correct class."""
        config = EmbeddingConfig(
            model="BAAI/bge-m3",
            provider="sentence-transformers",
            dimension=1024,
        )
        embedder = create_embedder(config)
        assert isinstance(embedder, _SentenceTransformerEmbedder)

    def test_creates_api_embedder(self) -> None:
        """api provider returns the correct class."""
        config = EmbeddingConfig(
            model="text-embedding-3-small",
            provider="api",
            dimension=1536,
            api_key_env="OPENAI_API_KEY",
            api_model="text-embedding-3-small",
        )
        embedder = create_embedder(config)
        assert isinstance(embedder, _APIEmbedder)

    def test_raises_on_unknown_provider(self) -> None:
        """An unknown provider raises a ValueError."""
        config = EmbeddingConfig(
            model="test",
            provider="nonexistent",
        )
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            create_embedder(config)

    def test_sentence_transformer_config_fields(self) -> None:
        """All config fields are propagated to the embedder instance."""
        config = EmbeddingConfig(
            model="nomic-ai/nomic-embed-text-v1.5",
            provider="sentence-transformers",
            dimension=768,
            device="cpu",
            batch_size=64,
        )
        embedder = create_embedder(config)
        assert embedder._config.model == "nomic-ai/nomic-embed-text-v1.5"
        assert embedder._config.dimension == 768
        assert embedder._config.device == "cpu"
        assert embedder._config.batch_size == 64

    def test_api_embedder_config_fields(self) -> None:
        """API embedder stores the correct model name and headers."""
        config = EmbeddingConfig(
            model="text-embedding-ada-002",
            provider="api",
            dimension=1536,
            api_key_env="OPENAI_API_KEY",
            api_model="text-embedding-ada-002",
        )
        embedder = create_embedder(config)
        assert embedder._api_model == "text-embedding-ada-002"
