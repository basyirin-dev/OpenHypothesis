"""Data models for the retrieval pipeline (not graph state).

These models are used internally by the ingestion and retrieval tools:
- ``PaperMetadata``: normalized paper record from API fetchers.
- ``Section``: a single section within a parsed paper (header + text body).
- ``ParsedDocument``: a full paper parsed from PDF, containing sections.
- ``DocumentChunk``: a single chunk produced by the semantic chunker, with
  an optional citation hash for cryptographic locking.

They live here rather than in ``state/schema.py`` because they are *tool-level*
DTOs, not part of the LangGraph discovery state.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PaperMetadata(BaseModel):
    """Normalized metadata for a single academic paper, as returned by any fetcher.

    All fetchers (OpenAlex, PubMed, bioRxiv) converge on this schema so the
    ingestion pipeline can handle papers uniformly.
    """

    doi: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    abstract: str = ""
    source: str = ""
    paper_url: str = ""
    pdf_url: str = ""
    publication_date: str = ""
    retrieved_at: datetime = Field(default_factory=_utcnow)


class Section(BaseModel):
    """A named section within a parsed paper (e.g. "Methods", "Discussion")."""

    header: str = ""
    text: str = ""


class ParsedDocument(BaseModel):
    """Full paper content extracted by a PDF parser.

    ``sections`` preserves the structural boundaries so the chunker can split
    semantically rather than blindly.
    """

    doi: str = ""
    title: str = ""
    sections: list[Section] = Field(default_factory=list)
    source: str = ""


class DocumentChunk(BaseModel):
    """A single chunk of text produced by the semantic chunker.

    ``citation_hash`` is computed as ``SHA256(doi + "|" + chunk_text + "|" + timestamp)``
    by ``CitationHasher`` after chunking but before Qdrant upsert.
    """

    chunk_id: str = ""
    doi: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    source: str = ""
    section_header: str = ""
    chunk_text: str = ""
    chunk_index: int = 0
    token_count: int = 0
    citation_hash: str = ""
    retrieval_timestamp: str = ""
