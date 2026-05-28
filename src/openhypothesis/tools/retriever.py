"""Qdrant vector database wrapper for scientific paper chunk storage and retrieval.

The ``VectorStore`` class manages a Qdrant collection configured with HNSW
index parameters tuned for high-dimensional scientific text embeddings.

Collection schema (``scientific_papers``):

- 1024-dimensional vectors (BGE-M3 default), cosine distance.
- Payload: doi, title, authors (list[str]), year, source, section_header,
  chunk_index, chunk_text, citation_hash, retrieval_timestamp.

Usage::

    from openhypothesis.config.schema import QdrantConfig
    from openhypothesis.tools.retriever import VectorStore

    config = QdrantConfig(host="localhost", port=6333)
    async with VectorStore(config) as store:
        await store.ensure_collection()
        results = await store.search(query_vector, top_k=10)
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http import models as qmodels

from openhypothesis.config.schema import QdrantConfig


class VectorStore:
    """High-level async wrapper around a Qdrant collection.

    Manages collection lifecycle, vector upsert, and similarity search with
    configurable HNSW parameters and payload filtering.

    Args:
        config: Qdrant connection and collection settings.
        prefer_grpc: Use gRPC for high-throughput operations.
        location: Override ``host``/``port`` with an in-memory or file-based
            Qdrant instance (e.g. ``":memory:"`` for testing). When set,
            ``config.host`` and ``config.port`` are ignored.
    """

    def __init__(
        self,
        config: QdrantConfig,
        prefer_grpc: bool = False,
        location: str | None = None,
    ) -> None:
        self._config = config
        self._prefer_grpc = prefer_grpc
        self._location = location
        self._client: AsyncQdrantClient | None = None
        self._sync_client: QdrantClient | None = None

    async def __aenter__(self) -> "VectorStore":
        await self._get_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            if self._location:
                self._client = AsyncQdrantClient(location=self._location)
            else:
                self._client = AsyncQdrantClient(
                    host=self._config.host,
                    port=self._config.port,
                    grpc_port=self._config.grpc_port,
                    prefer_grpc=self._prefer_grpc,
                )
        return self._client

    def _get_sync_client(self) -> QdrantClient:
        if self._sync_client is None:
            if self._location:
                self._sync_client = QdrantClient(location=self._location)
            else:
                self._sync_client = QdrantClient(
                    host=self._config.host,
                    port=self._config.port,
                    grpc_port=self._config.grpc_port,
                    prefer_grpc=self._prefer_grpc,
                )
        return self._sync_client

    async def collection_exists(self) -> bool:
        """Check whether the configured collection exists in Qdrant."""
        client = await self._get_client()
        collections = await client.get_collections()
        return any(c.name == self._config.collection for c in collections.collections)

    async def create_collection(self, vector_size: int | None = None) -> None:
        """Create the collection with HNSW config.

        Args:
            vector_size: Embedding dimension. Defaults to 1024 (BGE-M3).
        """
        client = await self._get_client()
        hnsw = self._config.hnsw

        await client.create_collection(
            collection_name=self._config.collection,
            vectors_config=qmodels.VectorParams(
                size=vector_size or 1024,
                distance=qmodels.Distance.COSINE,
                hnsw_config=qmodels.HnswConfigDiff(
                    m=hnsw.m,
                    ef_construct=hnsw.ef_construct,
                ),
            ),
            optimizers_config=qmodels.OptimizersConfigDiff(
                indexing_threshold=10000,
            ),
        )

    async def ensure_collection(self, vector_size: int | None = None) -> bool:
        """Create collection if it does not exist; no-op otherwise.

        Returns:
            ``True`` if the collection was created, ``False`` if it already existed.
        """
        if await self.collection_exists():
            return False
        await self.create_collection(vector_size=vector_size)
        return True

    async def delete_collection(self) -> None:
        """Drop the collection and all its data."""
        client = await self._get_client()
        await client.delete_collection(
            collection_name=self._config.collection,
            timeout=30,
        )

    async def upsert(
        self,
        points: list[qmodels.PointStruct],
        wait: bool = True,
    ) -> None:
        """Insert or update a batch of points.

        Args:
            points: List of ``PointStruct`` objects (id, vector, payload).
            wait: If ``True``, block until the operation is committed.
        """
        client = await self._get_client()
        await client.upsert(
            collection_name=self._config.collection,
            points=points,
            wait=wait,
        )

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        score_threshold: float | None = None,
        payload_filter: qmodels.Filter | None = None,
        with_payload: bool = True,
        with_vector: bool = False,
    ) -> list[qmodels.ScoredPoint]:
        """Search for the nearest neighbours of a query vector.

        Args:
            query_vector: The embedding vector to search with.
            top_k: Maximum number of results.
            score_threshold: Minimum cosine similarity score.
            payload_filter: Optional Qdrant filter for field-level constraints.
            with_payload: Include payload in results.
            with_vector: Include vectors in results (usually not needed).

        Returns:
            List of ``ScoredPoint`` sorted by descending score.
        """
        client = await self._get_client()
        search_params = qmodels.SearchParams(
            hnsw_ef=self._config.hnsw.ef_search,
            exact=False,
        )

        result = await client.query_points(
            collection_name=self._config.collection,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=payload_filter,
            search_params=search_params,
            with_payload=with_payload,
            with_vectors=with_vector,
        )
        return result.points

    async def batch_search(
        self,
        query_vectors: list[list[float]],
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[list[qmodels.ScoredPoint]]:
        """Search multiple query vectors in a single batch call.

        Args:
            query_vectors: List of embedding vectors.
            top_k: Maximum results per query.
            score_threshold: Minimum score filter.

        Returns:
            List of result lists, one per query vector.
        """
        client = await self._get_client()
        search_params = qmodels.SearchParams(
            hnsw_ef=self._config.hnsw.ef_search,
            exact=False,
        )

        requests = [
            qmodels.QueryRequest(
                query=qv,
                limit=top_k,
                score_threshold=score_threshold,
                params=search_params,
                with_payload=True,
                with_vector=False,
            )
            for qv in query_vectors
        ]

        results = await client.query_batch_points(
            collection_name=self._config.collection,
            requests=requests,
        )
        return [r.points for r in results]

    async def count(self, payload_filter: qmodels.Filter | None = None) -> int:
        """Count points in the collection, optionally filtered."""
        client = await self._get_client()
        result = await client.count(
            collection_name=self._config.collection,
            count_filter=payload_filter,
            exact=True,
        )
        return result.count

    async def close(self) -> None:
        """Close the underlying HTTP/gRPC connections."""
        if self._client is not None:
            await self._client.close()
            self._client = None
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None


@asynccontextmanager
async def open_store(config: QdrantConfig) -> AsyncIterator[VectorStore]:
    """Convenience async context manager for ``VectorStore``.

    Usage::

        async with open_store(qdrant_config) as store:
            await store.ensure_collection()
    """
    store = VectorStore(config)
    try:
        await store.__aenter__()
        yield store
    finally:
        await store.close()
