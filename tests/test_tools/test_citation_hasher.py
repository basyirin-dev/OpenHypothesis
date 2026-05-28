"""Tests for the CitationHasher cryptographic locking tool."""

from datetime import UTC, datetime

from openhypothesis.tools.citation_hasher import CitationHasher


class TestCitationHasher:
    """Determinism, verification, and edge-case handling."""

    def test_deterministic_hash(self) -> None:
        """Same inputs produce the same hash every time."""
        ts = datetime.now(UTC)
        h1 = CitationHasher.hash(doi="10.1234/abc", chunk_text="Gene X regulates Y.", timestamp=ts)
        h2 = CitationHasher.hash(doi="10.1234/abc", chunk_text="Gene X regulates Y.", timestamp=ts)
        assert h1 == h2

    def test_different_doi_different_hash(self) -> None:
        """Different DOIs produce different hashes."""
        ts = datetime.now(UTC)
        h1 = CitationHasher.hash(doi="10.1234/abc", chunk_text="Same text.", timestamp=ts)
        h2 = CitationHasher.hash(doi="10.5678/def", chunk_text="Same text.", timestamp=ts)
        assert h1 != h2

    def test_different_text_different_hash(self) -> None:
        """Different chunk text produces different hashes."""
        ts = datetime.now(UTC)
        h1 = CitationHasher.hash(doi="10.1234/abc", chunk_text="First version.", timestamp=ts)
        h2 = CitationHasher.hash(doi="10.1234/abc", chunk_text="Second version.", timestamp=ts)
        assert h1 != h2

    def test_different_timestamp_different_hash(self) -> None:
        """Different timestamps produce different hashes (prevents replay)."""
        ts1 = datetime(2025, 1, 1, tzinfo=UTC)
        ts2 = datetime(2025, 6, 1, tzinfo=UTC)
        h1 = CitationHasher.hash(doi="10.1234/abc", chunk_text="Text.", timestamp=ts1)
        h2 = CitationHasher.hash(doi="10.1234/abc", chunk_text="Text.", timestamp=ts2)
        assert h1 != h2

    def test_verify_positive(self) -> None:
        """verify() returns True for matching inputs."""
        ts = datetime.now(UTC)
        h = CitationHasher.hash(doi="10.1234/abc", chunk_text="Verify me.", timestamp=ts)
        assert CitationHasher.verify(doi="10.1234/abc", chunk_text="Verify me.", timestamp=ts, hash_value=h)  # noqa: E501

    def test_verify_negative_wrong_hash(self) -> None:
        """verify() returns False for a tampered hash."""
        ts = datetime.now(UTC)
        wrong_hash = "0" * 64
        assert not CitationHasher.verify(
            doi="10.1234/abc",
            chunk_text="Verify me.",
            timestamp=ts,
            hash_value=wrong_hash,
        )

    def test_empty_doi_defaults_to_unknown(self) -> None:
        """Empty DOI is normalized to ``'unknown'`` so hashing still works."""
        h = CitationHasher.hash(doi="", chunk_text="Some text.")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_doi_normalization(self) -> None:
        """DOI is lowercased and stripped."""
        ts = datetime.now(UTC)
        h1 = CitationHasher.hash(doi=" 10.1234/ABC ", chunk_text="Text.", timestamp=ts)
        h2 = CitationHasher.hash(doi="10.1234/abc", chunk_text="Text.", timestamp=ts)
        assert h1 == h2

    def test_hash_length_and_format(self) -> None:
        """Hash is a 64-character hex string."""
        h = CitationHasher.hash(doi="10.1234/x", chunk_text="Test.")
        assert len(h) == 64
        int(h, 16)  # raises ValueError if not hex

    def test_timestamp_defaults_to_now(self) -> None:
        """Omitting timestamp defaults to ``datetime.now(UTC)``."""
        h = CitationHasher.hash(doi="10.1234/x", chunk_text="Timeless.")
        assert isinstance(h, str)
        assert len(h) == 64
