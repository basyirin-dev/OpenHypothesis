"""FastMCP server exposing OpenHypothesis tools over the Model Context Protocol.

Usage (stdio, default)::

    uv run openhypothesis-mcp

Usage (SSE for production)::

    uv run openhypothesis-mcp --transport sse --port 8931

Usage (restricted tool set)::

    uv run openhypothesis-mcp --allow-tools search_papers,check_citation
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any

from openhypothesis.config.settings import Settings
from openhypothesis.state.checkpoint import create_checkpointer
from openhypothesis.state.schema import (
    Hypothesis,
    OpenHypothesisState,
)
from openhypothesis.tools.citation_hasher import CitationHasher
from openhypothesis.tools.model_router import ModelRouter

_MAX_RESULTS = 50


def _format_state_report(state: OpenHypothesisState) -> dict[str, Any]:
    """Convert a full ``OpenHypothesisState`` to a serializable audit dictionary."""
    return {
        "question": state.question.question,
        "domain": state.question.domain,
        "stage": state.stage,
        "total_cost_usd": state.total_cost_usd,
        "hypotheses": [
            {
                "id": h.id,
                "statement": h.statement,
                "confidence": h.confidence,
                "epistemic_tag": h.epistemic_tag.value,
                "generated_by": h.generated_by,
                "supporting_citations": [
                    {"doi": c.doi, "title": c.title, "nli_label": c.nli_label, "hash": c.hash}
                    for c in h.supporting_citations
                ],
                "contradicting_citations": [
                    {"doi": c.doi, "title": c.title, "nli_label": c.nli_label, "hash": c.hash}
                    for c in h.contradicting_citations
                ],
            }
            for h in state.hypotheses
        ],
        "graveyard": [
            {
                "id": h.id,
                "statement": h.statement,
                "epistemic_tag": h.epistemic_tag.value,
            }
            for h in state.graveyard
        ],
        "tournament_results": [
            {
                "hypothesis_id": r.hypothesis_id,
                "rank": r.rank,
                "weighted_score": r.weighted_score,
                "axis_scores": [
                    {"axis": a.axis, "score": a.score, "rationale": a.rationale}
                    for a in r.axis_scores
                ],
            }
            for r in state.tournament_results
        ],
        "feasibility_reports": {
            hid: {
                "overall_feasibility": r.overall_feasibility,
                "estimated_cost_usd": r.estimated_cost_usd,
                "estimated_timeline_weeks": r.estimated_timeline_weeks,
                "go_no_go": r.go_no_go,
                "required_reagents": [
                    {"name": i.name, "quantity": i.quantity, "estimated_cost_usd": i.estimated_cost_usd}
                    for i in r.required_reagents
                ],
                "required_equipment": r.required_equipment,
                "risk_factors": r.risk_factors,
            }
            for hid, r in state.feasibility_reports.items()
        },
    }


def _make_hypothesis_report(h: Hypothesis) -> dict[str, Any]:
    """Serialize a single ``Hypothesis`` for tool output."""
    return {
        "id": h.id,
        "statement": h.statement,
        "rationale": h.rationale,
        "confidence": h.confidence,
        "epistemic_tag": h.epistemic_tag.value,
        "generated_by": h.generated_by,
        "falsification_protocol": (
            {
                "experiment_design": h.falsification_protocol.experiment_design,
                "predicted_outcome": h.falsification_protocol.predicted_outcome,
                "key_assumptions": h.falsification_protocol.key_assumptions,
                "controls": h.falsification_protocol.controls,
            }
            if h.falsification_protocol
            else None
        ),
    }


def create_server(allowed_tools: set[str] | None = None) -> Any:
    """Build and return a configured ``FastMCP`` instance with optional tool filtering.

    Args:
        allowed_tools: If provided, only register tools whose names are in this set.
            When ``None``, all tools are registered.

    Returns:
        A ``FastMCP`` instance ready to run.
    """
    try:
        from fastmcp import FastMCP
    except ImportError as exc:
        raise ImportError(
            "fastmcp is required to run the MCP server. "
            "Install it with: uv sync --group mcp"
        ) from exc

    mcp = FastMCP("openhypothesis-mcp")

    def _allow(name: str) -> bool:
        return allowed_tools is None or name in allowed_tools

    # ------------------------------------------------------------------
    # Tool: search_papers
    # ------------------------------------------------------------------
    if _allow("search_papers"):

        @mcp.tool(
            name="search_papers",
            description="Search the indexed scientific paper corpus using semantic similarity.",
        )
        async def search_papers(
            query: str,
            top_k: int = 10,
            score_threshold: float | None = None,
        ) -> list[dict[str, Any]]:
            """Embed the query and retrieve the most relevant paper chunks from Qdrant.

            Args:
                query: Natural-language search query.
                top_k: Maximum number of results to return (max 50).
                score_threshold: Minimum cosine similarity score (0-1).

            Returns:
                List of scored results with payload and citation hash.
            """
            if top_k > _MAX_RESULTS:
                top_k = _MAX_RESULTS
            settings = Settings()
            config = settings.app_config
            try:
                from openhypothesis.tools.embedder import create_embedder

                embedder = create_embedder(config.embedding)
            except ImportError as exc:
                return [{"error": f"Embedding dependencies not installed: {exc}"}]

            try:
                vector = await embedder.embed(query)
            except Exception as exc:
                return [{"error": f"Embedding failed: {exc}"}]

            from openhypothesis.tools.retriever import open_store

            try:
                async with open_store(config.qdrant) as store:
                    results = await store.search(
                        query_vector=vector,
                        top_k=top_k,
                        score_threshold=score_threshold,
                    )
            except Exception as exc:
                return [{"error": f"Qdrant search failed: {exc}"}]

            output: list[dict[str, Any]] = []
            for r in results:
                p = r.payload or {}
                chunk_text = p.get("chunk_text", "")
                doi = p.get("doi", "")
                citation_hash = CitationHasher.hash(
                    doi=doi,
                    chunk_text=chunk_text,
                    timestamp=datetime.now(UTC),
                )
                output.append(
                    {
                        "score": round(r.score, 4),
                        "doi": doi,
                        "title": p.get("title", ""),
                        "authors": p.get("authors", []),
                        "year": p.get("year", 0),
                        "source": p.get("source", ""),
                        "section_header": p.get("section_header", ""),
                        "chunk_text": chunk_text,
                        "citation_hash": citation_hash,
                    }
                )
            return output

    # ------------------------------------------------------------------
    # Tool: check_citation
    # ------------------------------------------------------------------
    if _allow("check_citation"):

        @mcp.tool(
            name="check_citation",
            description="Verify or compute a cryptographic citation hash for a claim.",
        )
        async def check_citation(
            doi: str,
            chunk_text: str,
            expected_hash: str | None = None,
        ) -> dict[str, Any]:
            """Compute SHA256(DOI + chunk_text + timestamp) and optionally verify against a known hash.

            Args:
                doi: The DOI of the source paper.
                chunk_text: The exact text excerpt being cited.
                expected_hash: Optional 64-char hex hash to verify against.

            Returns:
                Computed hash and verification status.
            """
            timestamp = datetime.now(UTC)
            computed = CitationHasher.hash(doi=doi, chunk_text=chunk_text, timestamp=timestamp)
            result: dict[str, Any] = {
                "computed_hash": computed,
                "normalized_doi": CitationHasher._normalize_doi(doi),
                "timestamp": timestamp.isoformat(),
                "excerpt_preview": chunk_text[:200],
            }
            if expected_hash:
                verified = CitationHasher.verify(
                    doi=doi,
                    chunk_text=chunk_text,
                    timestamp=timestamp,
                    hash_value=expected_hash,
                )
                result["expected_hash"] = expected_hash
                result["verified"] = verified
            return result

    # ------------------------------------------------------------------
    # Tool: check_feasibility
    # ------------------------------------------------------------------
    if _allow("check_feasibility"):

        @mcp.tool(
            name="check_feasibility",
            description="Assess the wet-lab feasibility of a hypothesis or protocol.",
        )
        async def check_feasibility(
            hypothesis: str,
            domain: str = "",
        ) -> dict[str, Any]:
            """Use the LLM to reason about reagents, equipment, BSL level, timeline, and cost.

            Args:
                hypothesis: The hypothesis or protocol description.
                domain: Optional scientific domain (e.g. "biology", "chemistry").

            Returns:
                A structured feasibility report.
            """
            settings = Settings()
            config = settings.app_config
            profile = config.models.exploration if config.models else None
            model_id = f"{profile.provider}/{profile.model}" if profile else "openai/gpt-4o"

            system_prompt = (
                "You are a wet-lab feasibility analyst. Given a hypothesis or protocol, "
                "produce a structured JSON assessment covering: required reagents with estimated "
                "quantities and supplier pricing, required equipment, biosafety level (BSL-1 to "
                "BSL-4) with rationale, estimated timeline in weeks (optimistic and pessimistic), "
                "estimated total cost in USD, known failure modes, and a go/no-go recommendation. "
                "Output ONLY valid JSON with no markdown formatting."
            )
            user_prompt = f"Hypothesis: {hypothesis}\nDomain: {domain or 'general'}"

            try:
                router = ModelRouter(settings=settings)
                response = await router.agenerate(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw = response.content
            except Exception as exc:
                return {"error": f"LLM call failed: {exc}"}

            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {"raw_llm_output": raw, "error": "Failed to parse LLM response as JSON"}

            return {
                "overall_feasibility": parsed.get("overall_feasibility", 0.0),
                "estimated_timeline_weeks": parsed.get("estimated_timeline_weeks", 0),
                "estimated_cost_usd": parsed.get("estimated_cost_usd", 0.0),
                "biosafety_level": parsed.get("biosafety_level", "BSL-1"),
                "required_reagents": parsed.get("required_reagents", []),
                "required_equipment": parsed.get("required_equipment", []),
                "risk_factors": parsed.get("risk_factors", []),
                "go_no_go": parsed.get("go_no_go", False),
                "model_used": response.model_used,
                "cost_usd": response.cost.cost_usd,
            }

    # ------------------------------------------------------------------
    # Tool: search_negative_results
    # ------------------------------------------------------------------
    if _allow("search_negative_results"):

        @mcp.tool(
            name="search_negative_results",
            description="Search the corpus of prior failed experiments for a given target or mechanism.",
        )
        async def search_negative_results(
            target: str,
            top_k: int = 5,
        ) -> list[dict[str, Any]]:
            """Embed the target and search the ``negative_results`` Qdrant collection.

            Args:
                target: The biological target, mechanism, or gene name.
                top_k: Maximum number of results.

            Returns:
                List of previously failed attempts with payload details.
            """
            settings = Settings()
            config = settings.app_config
            try:
                from openhypothesis.tools.embedder import create_embedder

                embedder = create_embedder(config.embedding)
                vector = await embedder.embed(target)
            except Exception as exc:
                return [{"error": f"Embedding failed: {exc}"}]

            from openhypothesis.tools.retriever import open_store

            qdrant_config = config.qdrant.model_copy(update={"collection": "negative_results"})
            try:
                async with open_store(qdrant_config) as store:
                    exists = await store.collection_exists()
                    if not exists:
                        return []
                    results = await store.search(
                        query_vector=vector,
                        top_k=top_k,
                    )
            except Exception as exc:
                return [{"error": f"Qdrant search failed: {exc}"}]

            output: list[dict[str, Any]] = []
            for r in results:
                p = r.payload or {}
                output.append(
                    {
                        "score": round(r.score, 4),
                        "target": p.get("target", ""),
                        "mechanism": p.get("mechanism", ""),
                        "failure_reason": p.get("failure_reason", ""),
                        "doi": p.get("doi", ""),
                        "title": p.get("title", ""),
                        "year": p.get("year", 0),
                    }
                )
            return output

    # ------------------------------------------------------------------
    # Tool: generate_hypothesis
    # ------------------------------------------------------------------
    if _allow("generate_hypothesis"):

        @mcp.tool(
            name="generate_hypothesis",
            description="Generate novel scientific hypotheses for a research question.",
        )
        async def generate_hypothesis(
            question: str,
            domain: str = "",
            count: int = 3,
        ) -> list[dict[str, Any]]:
            """Use the LLM with a high-creativity prompt to produce diverse hypotheses.

            Args:
                question: The research question.
                domain: Optional scientific domain.
                count: Number of hypotheses to generate (max 10).

            Returns:
                List of hypothesis objects with statement, rationale, and confidence.
            """
            if count > 10:
                count = 10
            settings = Settings()
            config = settings.app_config
            profile = config.models.exploration if config.models else None
            model_id = f"{profile.provider}/{profile.model}" if profile else "openai/gpt-4o"

            system_prompt = (
                "You are a creative scientific hypothesis generator. Given a research question, "
                "produce diverse, novel, mechanistically plausible hypotheses. "
                "Output ONLY valid JSON as an array of objects with keys: "
                "statement (string), rationale (string), mechanism (string), "
                "expected_outcome (string), confidence (float 0-1). "
                "No markdown formatting."
            )
            user_prompt = f"Question: {question}\nDomain: {domain or 'general'}\nCount: {count}"

            try:
                router = ModelRouter(settings=settings)
                response = await router.agenerate(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw = response.content
            except Exception as exc:
                return [{"error": f"LLM call failed: {exc}"}]

            try:
                parsed = json.loads(raw)
                hypotheses = parsed if isinstance(parsed, list) else parsed.get("hypotheses", [parsed])
            except json.JSONDecodeError:
                return [{"raw_llm_output": raw, "error": "Failed to parse LLM response as JSON"}]

            return [
                {
                    "statement": h.get("statement", ""),
                    "rationale": h.get("rationale", ""),
                    "mechanism": h.get("mechanism", ""),
                    "expected_outcome": h.get("expected_outcome", ""),
                    "confidence": h.get("confidence", 0.5),
                    "model_used": response.model_used,
                    "cost_usd": response.cost.cost_usd / max(len(hypotheses), 1),
                }
                for h in hypotheses
            ]

    # ------------------------------------------------------------------
    # Tool: generate_audit_trail
    # ------------------------------------------------------------------
    if _allow("generate_audit_trail"):

        @mcp.tool(
            name="generate_audit_trail",
            description="Export a full provenance audit trail for a previous discovery session.",
        )
        async def generate_audit_trail(
            thread_id: str,
            output_format: str = "markdown",
        ) -> str:
            """Load the LangGraph checkpointer state and format a provenance report.

            Args:
                thread_id: The LangGraph thread ID from a prior ``/discover`` run.
                output_format: ``"markdown"`` or ``"json"``.

            Returns:
                Formatted audit trail string.
            """
            try:
                checkpointer = create_checkpointer()
                checkpointer_config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
                if hasattr(checkpointer, "aget"):
                    state_raw = await checkpointer.aget(checkpointer_config)  # type: ignore[arg-type]
                else:
                    state_raw = checkpointer.get(checkpointer_config)  # type: ignore[arg-type]
            except Exception as exc:
                return f"Error loading checkpointer state: {exc}"

            if state_raw is None:
                return f"No state found for thread_id: {thread_id}"

            from typing import cast as _cast

            if isinstance(state_raw, dict):
                raw_values: Any = state_raw.get("values", state_raw)
                state = OpenHypothesisState(**raw_values) if isinstance(raw_values, dict) else raw_values
            else:
                state = _cast(OpenHypothesisState, state_raw)

            report = _format_state_report(state)

            if output_format == "json":
                return json.dumps(report, indent=2, default=str)

            lines: list[str] = [
                f"# Audit Trail — {report['question']}",
                "",
                f"- **Domain:** {report['domain'] or 'N/A'}",
                f"- **Final Stage:** {report['stage']}",
                f"- **Total Cost:** ${report['total_cost_usd']:.4f}",
                "",
                f"## Hypotheses ({len(report['hypotheses'])})",
                "",
            ]
            tag_emoji = {
                "confirmed": "🟢",
                "plausible": "🟡",
                "speculative": "🔴",
                "contradicted": "⛔",
            }
            for h in report["hypotheses"]:
                emoji = tag_emoji.get(h["epistemic_tag"], "❓")
                lines.append(f"### {emoji} {h['statement'][:120]}")
                lines.append("")
                lines.append(f"- **ID:** {h['id']}")
                lines.append(f"- **Confidence:** {h['confidence']}")
                lines.append(f"- **Tag:** {h['epistemic_tag']}")
                lines.append(f"- **Generated by:** {h['generated_by']}")
                if h["supporting_citations"]:
                    lines.append(f"- **Citations:** {len(h['supporting_citations'])} supporting")
                if h["contradicting_citations"]:
                    lines.append(f"- **Contradictions:** {len(h['contradicting_citations'])}")
                lines.append("")

            if report["graveyard"]:
                lines.append(f"## Graveyard ({len(report['graveyard'])})")
                lines.append("")
                for g in report["graveyard"]:
                    lines.append(f"- {g['statement'][:100]}")
                lines.append("")

            if report["tournament_results"]:
                lines.append("## Tournament Rankings")
                lines.append("")
                lines.append("| Rank | Score | Hypothesis ID |")
                lines.append("|---|---|---|")
                for r in sorted(report["tournament_results"], key=lambda x: x["rank"]):
                    lines.append(f"| {r['rank']} | {r['weighted_score']:.4f} | {r['hypothesis_id'][:8]} |")
                lines.append("")

            if report["feasibility_reports"]:
                lines.append("## Feasibility Reports")
                lines.append("")
                for hid, fr in report["feasibility_reports"].items():
                    decision = "✅ Go" if fr["go_no_go"] else "❌ No-go"
                    lines.append(
                        f"- **{hid[:8]}:** {decision} "
                        f"| ${fr['estimated_cost_usd']:.0f} "
                        f"| {fr['estimated_timeline_weeks']}w "
                        f"| Score: {fr['overall_feasibility']}"
                    )
                lines.append("")

            return "\n".join(lines)

    return mcp


def main() -> None:
    """Entry point: parse CLI args and run the MCP server."""
    parser = argparse.ArgumentParser(
        description="OpenHypothesis MCP Server — exposes scientific discovery tools over MCP."
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse"],
        help="Transport protocol (stdio for local, sse for production).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8931,
        help="Port for SSE transport (default: 8931).",
    )
    parser.add_argument(
        "--allow-tools",
        default=None,
        help="Comma-separated list of tool names to enable (default: all).",
    )
    args = parser.parse_args()

    allowed: set[str] | None = None
    if args.allow_tools:
        allowed = {t.strip() for t in args.allow_tools.split(",") if t.strip()}

    try:
        mcp = create_server(allowed_tools=allowed)
    except ImportError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
