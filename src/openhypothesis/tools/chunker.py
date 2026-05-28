"""Semantic text chunking that respects scientific paper section boundaries.

The ``SemanticChunker`` splits a ``ParsedDocument`` into ``DocumentChunk``
instances by:

1. Treating each section (Abstract, Introduction, Methods, Results, Discussion,
   etc.) as a hard boundary — chunks never cross section boundaries.
2. Further splitting long sections into sentence-window sub-chunks with
   configurable target token count and overlap.

Section headers are detected via a known list of common scientific paper
section names.
"""

import re
from typing import Any

from openhypothesis.tools.models import DocumentChunk, ParsedDocument, Section

# Section headers that signal a hard chunk boundary. Regex is case-insensitive.
_SECTION_HEADERS: list[str] = [
    r"abstract",
    r"introduction",
    r"background",
    r"methods?",
    r"materials?\s+and\s+methods?",
    r"experimental\s+(procedures?|setup|methods?)",
    r"results?",
    r"discussion",
    r"conclusion",
    r"conclusions?",
    r"acknowledgment",
    r"acknowledgements?",
    r"references?",
    r"supplementary\s+(materials?|information|data|figures?)",
    r"appendix",
    r"figures?\s+and\s+tables?",
    r"data\s+availability",
    r"author\s+contributions?",
    r"competing\s+interests?",
    r"conflict\s+of\s+interest",
    r"funding",
    r"ethics?\s+statement",
]

_SECTION_PATTERN = re.compile(
    r"^(?:" + "|".join(_SECTION_HEADERS) + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _estimate_tokens(text: str) -> int:
    """Roughly estimate token count (4 characters per token on average)."""
    return max(1, len(text) // 4)


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences on period + space + capital letter boundaries.

    Simpler than a full NLP tokenizer; good enough for scientific abstracts and
    paper body text where sentence-final periods are followed by a space and an
    uppercase letter or opening quote.
    """
    sentence_end = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")
    parts = sentence_end.split(text)
    result: list[str] = []
    for part in parts:
        stripped = part.strip()
        if stripped:
            result.append(stripped)
    return result if result else [text.strip()]


class SemanticChunker:
    """Chunk a parsed document into semantically coherent pieces.

    Args:
        target_tokens: Preferred chunk size in tokens.
        max_tokens: Hard upper bound on chunk size.
        overlap_sentences: Number of overlapping sentences between consecutive
            chunks within the same section.
    """

    def __init__(
        self,
        target_tokens: int = 512,
        max_tokens: int = 1024,
        overlap_sentences: int = 2,
    ) -> None:
        self._target_tokens = target_tokens
        self._max_tokens = max_tokens
        self._overlap_sentences = overlap_sentences

    def chunk_document(
        self,
        document: ParsedDocument,
        **extra_payload: Any,
    ) -> list[DocumentChunk]:
        """Split a parsed document into chunks.

        Args:
            document: The parsed paper with pre-detected sections.
            **extra_payload: Additional fields to include in every chunk
                (e.g., ``doi``, ``title``, ``source``).

        Returns:
            List of ``DocumentChunk`` instances.
        """
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for section in document.sections:
            section_chunks = self._chunk_section(
                section=section,
                doi=document.doi or extra_payload.get("doi", ""),
                title=document.title or extra_payload.get("title", ""),
                source=document.source or extra_payload.get("source", ""),
            )
            for c in section_chunks:
                c.chunk_index = chunk_index
                chunk_index += 1
                chunks.append(c)

        return chunks

    def chunk_text(
        self,
        text: str,
        doi: str = "",
        title: str = "",
        source: str = "",
        **extra_payload: Any,
    ) -> list[DocumentChunk]:
        """Split a plain text string into chunks, auto-detecting section headers.

        Useful when sections are not pre-parsed (e.g., abstract-only metadata
        from API fetchers).
        """
        # Auto-detect section boundaries in raw text.
        sections = self._detect_sections(text)
        parsed = ParsedDocument(doi=doi, title=title, sections=sections, source=source)
        return self.chunk_document(parsed, **extra_payload)

    def _chunk_section(
        self,
        section: Section,
        doi: str,
        title: str,
        source: str,
    ) -> list[DocumentChunk]:
        """Split a single section into one or more chunks."""
        section_text = section.text.strip()
        if not section_text:
            return []

        header = section.header or ""

        # If the section fits in one chunk, return it directly.
        if _estimate_tokens(section_text) <= self._max_tokens:
            return [
                DocumentChunk(
                    doi=doi,
                    title=title,
                    source=source,
                    section_header=header,
                    chunk_text=section_text,
                    token_count=_estimate_tokens(section_text),
                )
            ]

        sentences = _split_into_sentences(section_text)
        if not sentences:
            return [
                DocumentChunk(
                    doi=doi,
                    title=title,
                    source=source,
                    section_header=header,
                    chunk_text=section_text,
                    token_count=_estimate_tokens(section_text),
                )
            ]

        return self._window_chunks(
            sentences=sentences,
            header=header,
            doi=doi,
            title=title,
            source=source,
        )

    def _window_chunks(
        self,
        sentences: list[str],
        header: str,
        doi: str,
        title: str,
        source: str,
    ) -> list[DocumentChunk]:
        """Build overlapping sentence-window chunks within a section."""
        chunks: list[DocumentChunk] = []
        start = 0

        while start < len(sentences):
            # Walk forward until we hit target_tokens or max_tokens.
            end = start
            token_count = 0
            while end < len(sentences):
                next_tokens = _estimate_tokens(sentences[end])
                if token_count + next_tokens > self._max_tokens:
                    break
                token_count += next_tokens
                end += 1
                if token_count >= self._target_tokens:
                    break

            # Ensure at least one sentence per chunk.
            if end == start:
                end = start + 1
                token_count = _estimate_tokens(sentences[start])

            chunk_text = " ".join(sentences[start:end])
            chunks.append(
                DocumentChunk(
                    doi=doi,
                    title=title,
                    source=source,
                    section_header=header,
                    chunk_text=chunk_text,
                    token_count=token_count,
                )
            )

            # Advance with overlap (move back by overlap_sentences sentences).
            advance = max(1, end - start - self._overlap_sentences)
            start += advance

        return chunks

    @staticmethod
    def _detect_sections(text: str) -> list[Section]:
        """Detect section boundaries in raw text using known header patterns.

        Falls back to a single "body" section if no headers are found.
        """
        lines = text.split("\n")
        sections: list[Section] = []
        current_header = ""
        current_lines: list[str] = []

        def flush() -> None:
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append(Section(header=current_header, text=body))

        for line in lines:
            stripped = line.strip()
            if _SECTION_PATTERN.match(stripped):
                flush()
                current_header = stripped
                current_lines = []
            else:
                current_lines.append(line)
        flush()

        if not sections:
            sections.append(Section(header="", text=text.strip()))

        return sections
