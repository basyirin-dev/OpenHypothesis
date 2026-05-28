"""Tests for the SemanticChunker tool."""


from openhypothesis.tools.chunker import SemanticChunker
from openhypothesis.tools.models import ParsedDocument, Section


class TestSemanticChunker:
    """Section boundary respect, token limits, and overlap behaviour."""

    def make_chunker(
        self, target_tokens: int = 512, max_tokens: int = 1024, overlap: int = 2
    ) -> SemanticChunker:
        return SemanticChunker(
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_sentences=overlap,
        )

    def test_single_short_section(self) -> None:
        """A single short section produces one chunk."""
        doc = ParsedDocument(
            doi="10.1234/test",
            title="Test Paper",
            sections=[Section(header="Abstract", text="This is a short abstract.")],
        )
        chunker = self.make_chunker()
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].section_header == "Abstract"
        assert chunks[0].chunk_text == "This is a short abstract."

    def test_multiple_sections_respect_boundaries(self) -> None:
        """Sections form hard boundaries — chunks never mix sections."""
        doc = ParsedDocument(
            doi="10.1234/test",
            title="Test Paper",
            sections=[
                Section(header="Introduction", text="Introduction text here."),
                Section(header="Methods", text="Methods text here."),
            ],
        )
        chunker = self.make_chunker()
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 2
        assert chunks[0].section_header == "Introduction"
        assert chunks[1].section_header == "Methods"
        assert "Introduction" in chunks[0].chunk_text
        assert "Methods" in chunks[1].chunk_text

    def test_long_section_is_split(self) -> None:
        """A section exceeding max_tokens is split into multiple chunks."""
        # Each sentence is ~100 chars / 25 tokens. 50 sentences = ~1250 tokens.
        sentence = "This is a sentence that repeats over and over again for testing. "
        long_text = sentence * 50
        doc = ParsedDocument(
            doi="10.1234/test",
            title="Test",
            sections=[Section(header="Results", text=long_text)],
        )
        chunker = self.make_chunker(target_tokens=100, max_tokens=200, overlap=0)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 1, "Long section should be split"
        for c in chunks:
            assert c.token_count <= 200, f"Chunk exceeds max_tokens: {c.token_count}"
            assert c.section_header == "Results"

    def test_chunks_have_correct_doi_and_title(self) -> None:
        """Every chunk inherits the document DOI and title."""
        doc = ParsedDocument(
            doi="10.1234/mydoi",
            title="My Paper",
            sections=[Section(header="Intro", text="Some intro text.")],
        )
        chunker = self.make_chunker()
        chunks = chunker.chunk_document(doc)
        assert all(c.doi == "10.1234/mydoi" for c in chunks)
        assert all(c.title == "My Paper" for c in chunks)

    def test_chunk_index_is_monotonic(self) -> None:
        """Chunk indices are sequential across all sections."""
        doc = ParsedDocument(
            doi="10.1234/test",
            title="Test",
            sections=[
                Section(header="A", text="Section A text."),
                Section(header="B", text="Section B text."),
            ],
        )
        chunker = self.make_chunker()
        chunks = chunker.chunk_document(doc)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_text_raw_text_no_sections(self) -> None:
        """chunk_text() handles raw text without pre-parsed sections."""
        chunker = self.make_chunker()
        chunks = chunker.chunk_text("This is raw text with no section headers.")
        assert len(chunks) == 1
        assert chunks[0].section_header == ""  # auto-detected: no headers found

    def test_chunk_text_with_detected_sections(self) -> None:
        """chunk_text() detects section headers in raw text."""
        raw = "Abstract\nThis is the abstract.\nMethods\nWe did stuff.\n"
        chunker = self.make_chunker()
        chunks = chunker.chunk_text(raw, doi="10.1/test", title="Test")
        assert len(chunks) == 2
        assert chunks[0].section_header == "Abstract"
        assert chunks[1].section_header == "Methods"

    def test_empty_section_produces_no_chunks(self) -> None:
        """An empty section is skipped."""
        doc = ParsedDocument(
            doi="10.1/x",
            title="X",
            sections=[Section(header="Empty", text="")],
        )
        chunker = self.make_chunker()
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 0

    def test_overlap_produces_overlapping_sentences(self) -> None:
        """Consecutive chunks from the same section share overlapping sentences."""
        # Build many short sentences so that with low target_tokens we get
        # multiple chunks with overlap.
        sentences = [f"Sentence number {i}. " for i in range(30)]
        text = "".join(sentences)
        doc = ParsedDocument(
            doi="10.1/x",
            title="X",
            sections=[Section(header="Long", text=text)],
        )
        chunker = self.make_chunker(
            target_tokens=10,   # ~2-3 sentences per chunk
            max_tokens=30,
            overlap=2,          # 2-sentence overlap
        )
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 2

        # Check that adjacent chunks share content (overlap).
        for i in range(len(chunks) - 1):
            c1_words = set(chunks[i].chunk_text.split())
            c2_words = set(chunks[i + 1].chunk_text.split())
            shared = c1_words & c2_words
            assert len(shared) > 0, f"Chunks {i} and {i+1} have no overlap"
