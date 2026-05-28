"""Tests for the VectorStore (Qdrant wrapper) using in-memory local mode.

Uses Qdrant's ``location=":memory:"`` mode to avoid needing a running
Docker container.
"""

import pytest
from qdrant_client.http import models as qmodels

from openhypothesis.config.schema import QdrantConfig
from openhypothesis.tools.retriever import VectorStore


@pytest.fixture
def store() -> VectorStore:
    """Return a VectorStore backed by an in-memory Qdrant instance."""
    config = QdrantConfig(collection="test_collection")
    return VectorStore(config, location=":memory:")


class TestVectorStore:
    """Collection lifecycle, upsert, search, and count."""

    @pytest.mark.asyncio
    async def test_create_and_check_collection(self, store: VectorStore) -> None:
        """Creating a collection and verifying existence works."""
        async with store:
            assert not await store.collection_exists()
            created = await store.ensure_collection(vector_size=4)
            assert created is True
            assert await store.collection_exists()

    @pytest.mark.asyncio
    async def test_collection_exists_idempotent(self, store: VectorStore) -> None:
        """ensure_collection is idempotent."""
        async with store:
            assert await store.ensure_collection(vector_size=4) is True
            assert await store.ensure_collection(vector_size=4) is False

    @pytest.mark.asyncio
    async def test_upsert_and_search(self, store: VectorStore) -> None:
        """Upserted points are findable via similarity search."""
        async with store:
            await store.ensure_collection(vector_size=4)

            points = [
                qmodels.PointStruct(
                    id=1,
                    vector=[1.0, 0.0, 0.0, 0.0],
                    payload={"doi": "10.1234/a", "title": "Paper A", "chunk_text": "Text A"},
                ),
                qmodels.PointStruct(
                    id=2,
                    vector=[0.0, 1.0, 0.0, 0.0],
                    payload={"doi": "10.1234/b", "title": "Paper B", "chunk_text": "Text B"},
                ),
                qmodels.PointStruct(
                    id=3,
                    vector=[0.0, 0.0, 1.0, 0.0],
                    payload={"doi": "10.1234/c", "title": "Paper C", "chunk_text": "Text C"},
                ),
            ]
            await store.upsert(points, wait=True)

            # Search for points similar to p1's vector.
            results = await store.search(query_vector=[1.0, 0.0, 0.0, 0.0], top_k=2)
            assert len(results) == 2
            assert results[0].id == 1
            assert results[0].score > 0.99  # identical vector

    @pytest.mark.asyncio
    async def test_search_with_score_threshold(self, store: VectorStore) -> None:
        """score_threshold filters out low-similarity results."""
        async with store:
            await store.ensure_collection(vector_size=4)

            points = [
                qmodels.PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"doi": "10.1/a"}),
                qmodels.PointStruct(id=2, vector=[0.0, 1.0, 0.0, 0.0], payload={"doi": "10.1/b"}),
            ]
            await store.upsert(points, wait=True)

            results = await store.search(
                query_vector=[1.0, 0.0, 0.0, 0.0],
                top_k=5,
                score_threshold=0.5,
            )
            assert len(results) == 1
            assert results[0].id == 1

    @pytest.mark.asyncio
    async def test_delete_collection(self, store: VectorStore) -> None:
        """Deleting a collection removes it."""
        async with store:
            await store.ensure_collection(vector_size=4)
            assert await store.collection_exists()
            await store.delete_collection()
            assert not await store.collection_exists()

    @pytest.mark.asyncio
    async def test_count_points(self, store: VectorStore) -> None:
        """count() returns the correct number of points."""
        async with store:
            await store.ensure_collection(vector_size=2)
            points = [
                qmodels.PointStruct(id=1, vector=[1.0, 0.0], payload={"doi": "10.1/a"}),
                qmodels.PointStruct(id=2, vector=[0.0, 1.0], payload={"doi": "10.1/b"}),
            ]
            await store.upsert(points, wait=True)
            assert await store.count() == 2

    @pytest.mark.asyncio
    async def test_batch_search(self, store: VectorStore) -> None:
        """batch_search returns result lists for each query."""
        async with store:
            await store.ensure_collection(vector_size=4)
            points = [
                qmodels.PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"doi": "10.1/a"}),
                qmodels.PointStruct(id=2, vector=[0.0, 1.0, 0.0, 0.0], payload={"doi": "10.1/b"}),
            ]
            await store.upsert(points, wait=True)

            results = await store.batch_search(
                query_vectors=[[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
                top_k=1,
            )
            assert len(results) == 2
            assert results[0][0].id == 1
            assert results[1][0].id == 2

    @pytest.mark.asyncio
    async def test_count_with_filter(self, store: VectorStore) -> None:
        """count() supports payload filtering."""
        async with store:
            await store.ensure_collection(vector_size=2)
            points = [
                qmodels.PointStruct(id=1, vector=[1.0, 0.0], payload={"source": "pubmed"}),
                qmodels.PointStruct(id=2, vector=[0.0, 1.0], payload={"source": "openalex"}),
            ]
            await store.upsert(points, wait=True)

            filtered = await store.count(
                payload_filter=qmodels.Filter(
                    must=[qmodels.FieldCondition(key="source", match=qmodels.MatchValue(value="pubmed"))],
                )
            )
            assert filtered == 1
