"""Cryptographic citation locking via SHA256 hashing.

Implements the ``CitationHasher`` which binds a citation to its source text via
``SHA256(DOI + chunk_text + retrieval_timestamp)``. This prevents "citation
drift" where downstream models hallucinate or modify cited claims without
invalidating the hash.

All agent nodes that emit ``Citation`` instances must call ``CitationHasher.hash``
before persisting.
"""

import hashlib
from datetime import UTC, datetime


class CitationHasher:
    """Deterministic SHA256 hasher for scientific citations.

    Usage::

        h = CitationHasher.hash(
            doi="10.1234/example",
            chunk_text="Gene X regulates Y via Z pathway.",
            timestamp=datetime.now(UTC),
        )
        assert CitationHasher.verify(
            doi="10.1234/example",
            chunk_text="Gene X regulates Y via Z pathway.",
            timestamp=datetime.now(UTC),
            hash=h,
        )
    """

    SEPARATOR = "|"

    @staticmethod
    def hash(
        doi: str,
        chunk_text: str,
        timestamp: datetime | None = None,
    ) -> str:
        """Compute ``SHA256(normalized_doi | chunk_text | timestamp_iso)``.

        Args:
            doi: The DOI of the source paper. Normalized to lowercase, stripped.
            chunk_text: The exact text excerpt being cited.
            timestamp: When the retrieval occurred. Defaults to UTC now.

        Returns:
            Hex-encoded SHA256 digest (64 characters).
        """
        norm_doi = CitationHasher._normalize_doi(doi)
        if timestamp is None:
            timestamp = datetime.now(UTC)
        ts = timestamp.isoformat()
        payload = f"{norm_doi}{CitationHasher.SEPARATOR}{chunk_text}{CitationHasher.SEPARATOR}{ts}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(
        doi: str,
        chunk_text: str,
        timestamp: datetime,
        hash_value: str,
    ) -> bool:
        """Verify that a hash matches the given inputs.

        Returns:
            ``True`` if ``hash_value`` equals ``hash(doi, chunk_text, timestamp)``.
        """
        expected = CitationHasher.hash(doi=doi, chunk_text=chunk_text, timestamp=timestamp)
        return hash_value == expected

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Lowercase and strip whitespace; default to ``"unknown"`` if empty."""
        cleaned = doi.strip().lower()
        return cleaned if cleaned else "unknown"
