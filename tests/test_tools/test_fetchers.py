"""Tests for the API fetcher classes with mocked HTTP responses."""

from unittest.mock import AsyncMock, patch

import pytest

from openhypothesis.tools.fetchers import (
    FetcherRegistry,
    OpenAlexFetcher,
    PaperMetadata,
    PubMedFetcher,
)


class TestOpenAlexFetcher:
    """OpenAlex response parsing."""

    SAMPLE_RESPONSE = {
        "results": [
            {
                "id": "https://openalex.org/W123456789",
                "doi": "https://doi.org/10.1234/abc.def",
                "title": "A Study of Gene Expression",
                "authorships": [
                    {
                        "author": {"display_name": "Alice Scientist"},
                    },
                    {
                        "author": {"display_name": "Bob Researcher"},
                    },
                ],
                "publication_year": 2024,
                "primary_location": {
                    "source": {"display_name": "Nature Genetics"},
                },
                "open_access": {
                    "is_oa": True,
                    "oa_url": "https://example.com/paper.pdf",
                },
                "abstract_inverted_index": {
                    "Gene": [0],
                    "expression": [1],
                    "regulates": [2],
                    "cancer": [3],
                },
            },
            {
                "id": "https://openalex.org/W987654321",
                "doi": "https://doi.org/10.5678/xyz",
                "title": "Another Paper Without Abstract",
                "authorships": [],
                "publication_year": 2023,
                "primary_location": None,
                "open_access": None,
                "abstract_inverted_index": None,
            },
        ],
    }

    @pytest.fixture
    def fetcher(self) -> OpenAlexFetcher:
        return OpenAlexFetcher()

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        client = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_fetch_returns_paper_metadata(self, fetcher: OpenAlexFetcher) -> None:
        """OpenAlex results are parsed into ``PaperMetadata`` instances."""
        with patch.object(fetcher, "_request", AsyncMock(return_value=self.SAMPLE_RESPONSE)):
            papers = await fetcher.fetch("gene expression")
            assert len(papers) == 2
            assert all(isinstance(p, PaperMetadata) for p in papers)

    @pytest.mark.asyncio
    async def test_doi_extraction(self, fetcher: OpenAlexFetcher) -> None:
        """Full DOI URLs are normalized to bare DOIs."""
        with patch.object(fetcher, "_request", AsyncMock(return_value=self.SAMPLE_RESPONSE)):
            papers = await fetcher.fetch("test")
            assert papers[0].doi == "10.1234/abc.def"

    @pytest.mark.asyncio
    async def test_abstract_reconstruction(self, fetcher: OpenAlexFetcher) -> None:
        """Inverted-index abstracts are correctly reconstructed."""
        with patch.object(fetcher, "_request", AsyncMock(return_value=self.SAMPLE_RESPONSE)):
            papers = await fetcher.fetch("test")
            assert papers[0].abstract == "Gene expression regulates cancer"

    @pytest.mark.asyncio
    async def test_authors_parsed(self, fetcher: OpenAlexFetcher) -> None:
        """Author list is correctly extracted."""
        with patch.object(fetcher, "_request", AsyncMock(return_value=self.SAMPLE_RESPONSE)):
            papers = await fetcher.fetch("test")
            assert papers[0].authors == ["Alice Scientist", "Bob Researcher"]

    @pytest.mark.asyncio
    async def test_missing_abstract(self, fetcher: OpenAlexFetcher) -> None:
        """Papers without abstracts still parse successfully."""
        with patch.object(fetcher, "_request", AsyncMock(return_value=self.SAMPLE_RESPONSE)):
            papers = await fetcher.fetch("test")
            assert papers[1].abstract == ""


class TestPubMedFetcher:
    """PubMed XML response parsing."""

    SAMPLE_XML = """<?xml version="1.0"?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticleSet 2.0//EN"
  "https://dtd.nlm.nih.gov/ncbi/pubmed/out/PubMedArticleSet.dtd">
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE" Owner="NLM">
      <PMID Version="1">12345678</PMID>
      <Article PubModel="Print">
        <Journal>
          <Title>Journal of Test Science</Title>
        </Journal>
        <ArticleTitle>A Test Article About CRISPR</ArticleTitle>
        <AuthorList>
          <Author>
            <LastName>Smith</LastName>
            <ForeName>John</ForeName>
          </Author>
          <Author>
            <LastName>Doe</LastName>
            <ForeName>Jane</ForeName>
          </Author>
        </AuthorList>
        <Abstract>
          <AbstractText Label="Background">This is the background.</AbstractText>
          <AbstractText Label="Methods">We tested things.</AbstractText>
        </Abstract>
        <PubDate>
          <Year>2024</Year>
        </PubDate>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/crispr.2024</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>"""

    @pytest.fixture
    def fetcher(self) -> PubMedFetcher:
        return PubMedFetcher()

    @pytest.mark.asyncio
    async def test_parse_xml(self, fetcher: PubMedFetcher) -> None:
        """PubMed XML is correctly parsed into PaperMetadata."""
        papers = fetcher._parse_xml(self.SAMPLE_XML)
        assert len(papers) == 1
        p = papers[0]
        assert p.doi == "10.1234/crispr.2024"
        assert p.title == "A Test Article About CRISPR"
        assert p.authors == ["Smith John", "Doe Jane"]
        assert p.year == 2024
        assert "Background: This is the background." in p.abstract
        assert "Methods: We tested things." in p.abstract

    @pytest.mark.asyncio
    async def test_empty_xml_returns_empty(self, fetcher: PubMedFetcher) -> None:
        """Malformed or empty XML returns an empty list."""
        papers = fetcher._parse_xml("<not-pubmed/>")
        assert papers == []


class TestFetcherRegistry:
    """Registry dedup and fan-out."""

    @pytest.mark.asyncio
    async def test_dedup_by_doi(self) -> None:
        """Duplicate DOIs across sources are merged (only one kept)."""
        registry = FetcherRegistry()

        # Mock both fetchers to return a paper with the same DOI.
        async def fake_fetch(_query: str, _max_results: int = 25, **_kwargs: str) -> list[PaperMetadata]:  # noqa: ARG001
            return [
                PaperMetadata(
                    doi="10.1234/duplicate",
                    title="Same Paper",
                    authors=["Author A"],
                    year=2024,
                    abstract="Same abstract.",
                    source="openalex",
                ),
            ]

        registry._fetchers["openalex"] = AsyncMock(fetch=fake_fetch)
        registry._fetchers["pubmed"] = AsyncMock(fetch=fake_fetch)

        papers = await registry.fetch("test", sources=["openalex", "pubmed"], max_results=10)
        assert len(papers) == 1  # deduplicated
        assert papers[0].doi == "10.1234/duplicate"
