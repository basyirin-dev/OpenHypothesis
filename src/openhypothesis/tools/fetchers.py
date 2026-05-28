"""Async API fetchers for academic paper metadata.

Provides three fetcher implementations that converge on the ``PaperMetadata``
model, plus a ``FetcherRegistry`` for unified dispatch across sources.

Sources
-------
- **OpenAlex**: comprehensive open scholarly index (covers PubMed, bioRxiv, etc.)
- **PubMed**: NCBI E-Utilities for biomedical literature.
- **bioRxiv**: preprint server API for life sciences.

Usage::

    registry = FetcherRegistry()
    papers = await registry.fetch("CRISPR gene editing", sources=["openalex"])
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from typing import Any
from xml.parsers.expat import ExpatError

import httpx

from openhypothesis.tools.models import PaperMetadata

# Default HTTP timeouts for API calls (in seconds).
_DEFAULT_TIMEOUT = 30.0
_MAX_RETRIES = 3
_BASE_RETRY_DELAY = 1.5


def _parse_openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct an abstract from OpenAlex's inverted-index format.

    Each key is a word, and its value is a list of positions where that word
    appears. We reconstruct by sorting all (position, word) pairs.
    """
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def _extract_doi_from_url(url: str) -> str:
    """Extract a bare DOI from a full ``https://doi.org/...`` URL."""
    match = re.search(r"10\.\S+", url)
    return match.group(0) if match else url


class BaseFetcher(ABC):
    """Abstract base for an academic paper API fetcher.

    Subclasses implement ``_fetch_page`` to call their specific API and handle
    rate limiting, timeouts, and error recovery via the shared ``_request`` method.
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    @abstractmethod
    async def fetch(
        self, query: str, max_results: int = 25, **kwargs: Any
    ) -> list[PaperMetadata]:
        """Search the source and return normalized paper metadata."""
        ...

    async def _request(
        self, url: str, params: dict[str, Any] | None = None
    ) -> Any:
        """Perform an HTTP GET with retries and rate-limit awareness.

        Retries up to ``_MAX_RETRIES`` times with exponential backoff.
        Raises ``httpx.HTTPStatusError`` on non-2xx after exhausting retries.
        """
        client = self._client or _get_default_client()
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await client.get(url, params=params)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", _BASE_RETRY_DELAY))
                    await asyncio.sleep(retry_after * (2**attempt))
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "xml" in content_type or "text/xml" in content_type:
                    return response.text
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                await asyncio.sleep(_BASE_RETRY_DELAY * (2**attempt))

        raise httpx.HTTPStatusError(
            f"Request failed after {_MAX_RETRIES} retries",
            request=getattr(last_exc, "request", None),  # type: ignore[arg-type]
            response=getattr(last_exc, "response", None),  # type: ignore[arg-type]
        )


_client_instance: httpx.AsyncClient | None = None


def _get_default_client() -> httpx.AsyncClient:
    """Return a module-level shared ``httpx.AsyncClient``.

    Lazily created on first call; intended for use by fetchers that weren't
    given an explicit client.
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _client_instance


class OpenAlexFetcher(BaseFetcher):
    """Fetcher for the OpenAlex open scholarly index.

    Covers all disciplines; results include both published and preprint works.
    """

    BASE_URL = "https://api.openalex.org"

    async def fetch(
        self, query: str, max_results: int = 25, **kwargs: Any
    ) -> list[PaperMetadata]:
        params: dict[str, Any] = {
            "search": query,
            "per_page": min(max_results, 200),
            "sort": "relevance_score:desc",
            "mailto": kwargs.get("mailto", ""),
        }
        data = await self._request(f"{self.BASE_URL}/works", params=params)
        results = data.get("results", []) if isinstance(data, dict) else []
        return [self._to_metadata(item) for item in results[:max_results]]

    @staticmethod
    def _to_metadata(item: dict[str, Any]) -> PaperMetadata:
        doi_url = item.get("doi", "")
        doi = _extract_doi_from_url(doi_url) if doi_url else ""

        authors = [
            a.get("author", {}).get("display_name", "")
            for a in item.get("authorships", [])
        ]
        authors = [a for a in authors if a]

        raw_abstract = item.get("abstract_inverted_index")
        abstract = _parse_openalex_abstract(raw_abstract)

        source_info = item.get("primary_location", {}) or {}
        source_name = ""
        if source_info.get("source"):
            source_name = source_info["source"].get("display_name", "")

        pdf_url = ""
        oa = item.get("open_access", {}) or {}
        if oa.get("is_oa") and oa.get("oa_url"):
            pdf_url = oa["oa_url"]

        return PaperMetadata(
            doi=doi,
            title=item.get("title", ""),
            authors=authors,
            year=item.get("publication_year", 0),
            abstract=abstract,
            source=source_name or "openalex",
            paper_url=item.get("id", ""),
            pdf_url=pdf_url,
        )


class PubMedFetcher(BaseFetcher):
    """Fetcher for PubMed / PubMed Central via NCBI E-Utilities.

    Uses ESearch for ID lookup and EFetch for full metadata retrieval.
    """

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    async def fetch(
        self, query: str, max_results: int = 25, **kwargs: Any  # noqa: ARG002
    ) -> list[PaperMetadata]:
        # Step 1: search for PMIDs
        search_params: dict[str, Any] = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        search_data = await self._request(self.ESEARCH_URL, params=search_params)
        id_list = (
            search_data.get("esearchresult", {}).get("idlist", []) if isinstance(search_data, dict)
            else []
        )
        if not id_list:
            return []

        # Step 2: fetch metadata for found PMIDs
        fetch_params: dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
        }
        xml_text = await self._request(self.EFETCH_URL, params=fetch_params)
        if not isinstance(xml_text, str):
            return []

        return self._parse_xml(xml_text)[:max_results]

    @staticmethod
    def _parse_xml(xml_text: str) -> list[PaperMetadata]:
        """Parse PubMed XML response into ``PaperMetadata`` list."""
        papers: list[PaperMetadata] = []
        try:
            root = ET.fromstring(xml_text)
        except ExpatError:
            return papers

        for article_elem in root.iter("PubmedArticle"):
            try:
                medline = article_elem.find(".//MedlineCitation")
                if medline is None:
                    continue
                article = medline.find(".//Article")
                if article is None:
                    continue

                title_el = article.find("ArticleTitle")
                title = "".join(title_el.itertext()) if title_el is not None else ""

                authors: list[str] = []
                author_list = article.find(".//AuthorList")
                if author_list is not None:
                    for author in author_list.findall("Author"):
                        last = author.find("LastName")
                        fore = author.find("ForeName")
                        if last is not None and fore is not None:
                            authors.append(f"{last.text} {fore.text}")

                year_el = article.find(".//PubDate/Year")
                year = int(year_el.text) if year_el is not None and year_el.text else 0

                abstract_parts: list[str] = []
                abstract_elements = article.findall(".//Abstract/AbstractText")
                for el in abstract_elements:
                    label = el.get("Label", "")
                    text = "".join(el.itertext())
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)
                abstract = " ".join(abstract_parts)

                doi = ""
                # Check MedlineCitation ELocationID first.
                for eid in medline.findall(".//ELocationID"):
                    if eid.get("EIdType") == "doi":
                        doi = eid.text or ""
                        break
                # Fall back to PubmedData ArticleIdList.
                if not doi:
                    pubmed_data = article_elem.find("PubmedData")
                    if pubmed_data is not None:
                        for aid in pubmed_data.findall(".//ArticleId"):
                            if aid.get("IdType") == "doi":
                                doi = aid.text or ""
                                break

                source = "PubMed"
                journal = article.find("Journal/Title")
                if journal is not None and journal.text:
                    source = journal.text

                papers.append(
                    PaperMetadata(
                        doi=doi,
                        title=title,
                        authors=authors,
                        year=year,
                        abstract=abstract,
                        source=source,
                    )
                )
            except (AttributeError, TypeError, ValueError):
                continue
        return papers


class BioRxivFetcher(BaseFetcher):
    """Fetcher for bioRxiv / medRxiv preprints.

    bioRxiv's API is date-based rather than query-based, so we retrieve recent
    papers and filter client-side by keyword matching. For production use,
    this is best paired with OpenAlex as the primary search index.
    """

    BASE_URL = "https://api.biorxiv.org/details/biorxiv"

    async def fetch(
        self, query: str, max_results: int = 25, **kwargs: Any
    ) -> list[PaperMetadata]:
        cursor = kwargs.get("cursor", 0)
        url = f"{self.BASE_URL}/2000-01-01/2030-12-31/{cursor}"
        data = await self._request(url)
        collection = data.get("collection", []) if isinstance(data, dict) else []
        if not collection:
            return []

        query_lower = query.lower()
        matched: list[PaperMetadata] = []
        for item in collection:
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            authors_raw = item.get("authors", "")
            if not any(
                q in title.lower() or q in abstract.lower() for q in query_lower.split()
            ):
                continue

            author_list = [a.strip() for a in authors_raw.split(";") if a.strip()]

            matched.append(
                PaperMetadata(
                    doi=item.get("doi", ""),
                    title=title,
                    authors=author_list,
                    year=item.get("date", "")[:4] if item.get("date") else 0,
                    abstract=abstract,
                    source="bioRxiv",
                    paper_url=f"https://www.biorxiv.org/content/{item.get('doi', '')}",
                    pdf_url=f"https://www.biorxiv.org/content/{item.get('doi', '')}.full.pdf",
                )
            )
            if len(matched) >= max_results:
                break
        return matched


class FetcherRegistry:
    """Registry that dispatches ``fetch()`` calls to the appropriate fetchers.

    Usage::

        registry = FetcherRegistry()
        papers = await registry.fetch(
            "machine learning drug discovery",
            sources=["openalex", "pubmed"],
            max_results=50,
        )
    """

    FETCHER_MAP: dict[str, type[BaseFetcher]] = {
        "openalex": OpenAlexFetcher,
        "pubmed": PubMedFetcher,
        "biorxiv": BioRxivFetcher,
    }

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._fetchers: dict[str, BaseFetcher] = {}

    def _get_fetcher(self, name: str) -> BaseFetcher:
        if name not in self._fetchers:
            cls = self.FETCHER_MAP[name]
            self._fetchers[name] = cls(client=self._client)
        return self._fetchers[name]

    async def fetch(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results: int = 25,
        **kwargs: Any,
    ) -> list[PaperMetadata]:
        """Fan out the query to multiple sources and merge results.

        Args:
            query: Free-text search query.
            sources: List of source names (defaults to all registered).
            max_results: Maximum total results across all sources.
            **kwargs: Passed through to each fetcher.

        Returns:
            Deduplicated (by DOI) list of ``PaperMetadata``, sorted by source
            priority (OpenAlex first, then PubMed, then bioRxiv).
        """
        if sources is None:
            sources = list(self.FETCHER_MAP)

        tasks = [
            self._get_fetcher(name).fetch(query, max_results=max_results, **kwargs)
            for name in sources
            if name in self.FETCHER_MAP
        ]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        seen_dois: set[str] = set()
        merged: list[PaperMetadata] = []
        for results in results_lists:
            if isinstance(results, BaseException):
                continue
            for paper in results:
                if paper.doi and paper.doi not in seen_dois:
                    seen_dois.add(paper.doi)
                    merged.append(paper)

        return merged[:max_results]
