"""Data ingestion pipeline for populating the Qdrant knowledge base.

Flow::

    HTTP APIs (OpenAlex, PubMed, bioRxiv)
        │  FetcherRegistry.fetch()
        ▼
    PaperMetadata list
        │  PDFParser.parse()  [optional — falls back to abstract]
        ▼
    ParsedDocument list
        │  SemanticChunker.chunk_document()
        ▼
    DocumentChunk list
        │  CitationHasher.hash()
        ▼
    Chunks with citation hashes
        │  EmbeddingModel.embed_batch()
        ▼
    Vectors + payload
        │  VectorStore.upsert()
        ▼
    Qdrant collection

Usage from CLI::

    uv run python -m openhypothesis.tools.ingest "crispr gene editing" \\
        --sources openalex pubmed --max-papers 10

Usage from Python::

    from openhypothesis.tools.ingest import ingest_pipeline
    stats = await ingest_pipeline("cancer immunotherapy", sources=["openalex"])
"""

import argparse
import asyncio
import logging
import os
import tempfile
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from qdrant_client.http import models as qmodels

from openhypothesis.config.settings import Settings
from openhypothesis.tools.chunker import SemanticChunker
from openhypothesis.tools.citation_hasher import CitationHasher
from openhypothesis.tools.embedder import EmbeddingModel, create_embedder
from openhypothesis.tools.fetchers import FetcherRegistry
from openhypothesis.tools.models import DocumentChunk, PaperMetadata, ParsedDocument, Section
from openhypothesis.tools.retriever import VectorStore

logger = logging.getLogger(__name__)


async def _try_parse_pdf(pdf_url: str, doi: str, title: str, source: str) -> ParsedDocument | None:
    """Attempt to parse a PDF into a ``ParsedDocument``.

    Tries ``marker`` first, then ``nougat``, then falls back to ``None``
    (caller uses abstract text instead). Exceptions are logged but not raised.
    """
    if not pdf_url:
        return None

    try:
        import httpx

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
            pdf_bytes = response.content
    except Exception as exc:
        logger.warning("Failed to download PDF from %s: %s", pdf_url, exc)
        return None

    if not pdf_bytes or len(pdf_bytes) < 100:
        return None

    # Try marker.
    try:
        from marker.convert import convert_pdf  # type: ignore[import-untyped, import-not-found]

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            full_text, _, _ = convert_pdf(tmp_path)
        except Exception:
            full_text = None
        finally:
            os.unlink(tmp_path)

        if full_text:
            # marker returns markdown; detect sections via line-based headers.
            sections = _detect_sections_from_text(str(full_text))
            return ParsedDocument(doi=doi, title=title, sections=sections, source=source)
    except ImportError:
        logger.debug("marker not available, trying nougat")
    except Exception as exc:
        logger.warning("marker parsing failed for %s: %s", doi, exc)

    # Try nougat.
    try:
        from nougat import NougatModel  # type: ignore[import-untyped, import-not-found]
        from nougat.utils.checkpoint import get_checkpoint
        from nougat.utils.dataset import Dataset

        checkpoint = get_checkpoint()
        model = NougatModel.from_pretrained(checkpoint)
        model.to("cpu")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            dataset = Dataset([tmp_path])
            for page in dataset:
                if page is not None:
                    prediction = model.inference(page)
                    text = prediction["prediction"]
                    sections = _detect_sections_from_text(text)
                    return ParsedDocument(
                        doi=doi, title=title, sections=sections, source=source
                    )
        finally:
            os.unlink(tmp_path)
    except ImportError:
        logger.debug("nougat not available either, using abstract fallback")
    except Exception as exc:
        logger.warning("nougat parsing failed for %s: %s", doi, exc)

    return None


def _detect_sections_from_text(text: str) -> list[Section]:
    """Simple section detection from a plain text string.

    Splits on common scientific paper section headers.
    """
    lines = text.split("\n")
    sections: list[Section] = []
    current_header = ""
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and (
            stripped.lower().rstrip(".").rstrip()
            in [
                "abstract",
                "introduction",
                "background",
                "methods",
                "results",
                "discussion",
                "conclusion",
                "acknowledgments",
                "references",
            ]
        ):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append(Section(header=current_header, text=body))
            current_header = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(Section(header=current_header, text=body))

    if not sections:
        sections.append(Section(text=text.strip()))

    return sections


def _paper_to_document(paper: PaperMetadata) -> ParsedDocument:
    """Convert a ``PaperMetadata`` (from API fetcher) into a ``ParsedDocument``.

    Uses the abstract text as a single section when full PDF is unavailable.
    """
    sections = (
        [Section(header="Abstract", text=paper.abstract)]
        if paper.abstract
        else [Section(text=f"{paper.title}")]
    )
    return ParsedDocument(doi=paper.doi, title=paper.title, sections=sections, source=paper.source)


async def ingest_pipeline(
    query: str,
    sources: list[str] | None = None,
    max_papers: int = 25,
    reindex: bool = False,
    dry_run: bool = False,
    config_path: str = "config.yaml",
) -> dict[str, Any]:
    """Run the full ingestion pipeline.

    Args:
        query: Free-text search query for paper APIs.
        sources: API sources to query (defaults to all).
        max_papers: Maximum number of papers to fetch and index.
        reindex: Drop and recreate the Qdrant collection before indexing.
        dry_run: Fetch and parse but do not index into Qdrant.
        config_path: Path to the YAML config file.

    Returns:
        A stats dict with keys:
        - ``papers_fetched``: total papers found across all sources.
        - ``papers_parsed``: papers successfully parsed (PDF or abstract).
        - ``chunks_created``: total chunks after semantic chunking.
        - ``chunks_indexed``: chunks written to Qdrant (0 in dry-run mode).
        - ``sources_used``: list of API source names.
        - ``errors``: list of error messages (non-fatal).
    """
    settings = Settings(config_path=config_path)
    app_config = settings.app_config

    embedder: EmbeddingModel | None = None
    store: VectorStore | None = None
    errors: list[str] = []

    try:
        embedder = create_embedder(app_config.embedding)
    except (ImportError, ValueError) as exc:
        errors.append(f"Embedder init: {exc}")
        logger.warning("Proceeding without embedder (dry-run stats only)")

    # Step 1: Fetch papers.
    fetcher = FetcherRegistry()
    papers = await fetcher.fetch(
        query=query,
        sources=sources,
        max_results=max_papers,
    )
    logger.info("Fetched %d papers from %s", len(papers), sources or "all")

    if not papers:
        return {
            "papers_fetched": 0,
            "papers_parsed": 0,
            "chunks_created": 0,
            "chunks_indexed": 0,
            "sources_used": sources or list(FetcherRegistry.FETCHER_MAP),
            "errors": errors + ["No papers found for query"],
        }

    # Step 2: Parse papers (PDF or abstract fallback).
    chunker = SemanticChunker()
    all_chunks: list[DocumentChunk] = []
    papers_parsed = 0

    for paper in papers:
        parsed: ParsedDocument | None = None

        if paper.pdf_url:
            parsed = await _try_parse_pdf(paper.pdf_url, paper.doi, paper.title, paper.source)

        if parsed is None:
            parsed = _paper_to_document(paper)

        if parsed:
            papers_parsed += 1
            chunks = chunker.chunk_document(parsed)
            all_chunks.extend(chunks)

    logger.info("Parsed %d papers into %d chunks", papers_parsed, len(all_chunks))

    # Step 3: Compute citation hashes.
    now = datetime.now(UTC)
    for chunk in all_chunks:
        chunk.citation_hash = CitationHasher.hash(
            doi=chunk.doi,
            chunk_text=chunk.chunk_text,
            timestamp=now,
        )
        chunk.retrieval_timestamp = now.isoformat()
        chunk.chunk_id = uuid4().hex

    if dry_run or embedder is None:
        return {
            "papers_fetched": len(papers),
            "papers_parsed": papers_parsed,
            "chunks_created": len(all_chunks),
            "chunks_indexed": 0,
            "sources_used": list({p.source for p in papers}),
            "errors": errors,
        }

    # Step 4: Embed chunks.
    chunk_texts = [c.chunk_text for c in all_chunks]
    embeddings = await embedder.embed_batch(chunk_texts)
    logger.info("Computed %d embeddings", len(embeddings))

    # Step 5: Index into Qdrant.
    store = VectorStore(app_config.qdrant)
    await store.__aenter__()

    if reindex:
        if await store.collection_exists():
            await store.delete_collection()
        await store.ensure_collection(vector_size=app_config.embedding.dimension)
    else:
        await store.ensure_collection(vector_size=app_config.embedding.dimension)

    points: list[qmodels.PointStruct] = []
    for chunk, vector in zip(all_chunks, embeddings, strict=True):
        points.append(
            qmodels.PointStruct(
                id=chunk.chunk_id,
                vector=vector,
                payload={
                    "doi": chunk.doi,
                    "title": chunk.title,
                    "authors": chunk.authors,
                    "year": chunk.year,
                    "source": chunk.source,
                    "section_header": chunk.section_header,
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.chunk_text,
                    "token_count": chunk.token_count,
                    "citation_hash": chunk.citation_hash,
                    "retrieval_timestamp": chunk.retrieval_timestamp,
                },
            )
        )

    # Upsert in batches of 100.
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        await store.upsert(batch, wait=True)

    indexed_count = len(points)
    await store.close()

    logger.info("Indexed %d chunks into Qdrant collection '%s'", indexed_count, store._config.collection)

    return {
        "papers_fetched": len(papers),
        "papers_parsed": papers_parsed,
        "chunks_created": len(all_chunks),
        "chunks_indexed": indexed_count,
        "sources_used": list({p.source for p in papers}),
        "errors": errors,
    }


def main() -> None:
    """CLI entry point for ``python -m openhypothesis.tools.ingest``."""
    parser = argparse.ArgumentParser(
        description="Ingest scientific papers into the Qdrant knowledge base.",
    )
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument(
        "--sources",
        type=str,
        nargs="+",
        default=None,
        help="API sources (default: all)",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=25,
        help="Maximum papers to fetch (default: 25)",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Drop and recreate the Qdrant collection before indexing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse but do not index into Qdrant",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    stats = asyncio.run(
        ingest_pipeline(
            query=args.query,
            sources=args.sources,
            max_papers=args.max_papers,
            reindex=args.reindex,
            dry_run=args.dry_run,
            config_path=args.config,
        )
    )

    print("\n=== Ingestion Summary ===")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print("========================")


if __name__ == "__main__":
    main()
