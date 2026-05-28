import operator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    """Return the current UTC datetime. Used as the default factory for timestamp fields."""
    return datetime.now(UTC)


class EpistemicTag(StrEnum):
    """Epistemic status of a hypothesis, ordered from most to least certain.

    - CONFIRMED: validated by independent replication or NLI-confirmed evidence.
    - PLAUSIBLE: supported by at least one credible citation but not rigorously confirmed.
    - SPECULATIVE: proposed without supporting evidence; default for all new hypotheses.
    - CONTRADICTED: actively refuted by experimental or literature evidence.
    """

    CONFIRMED = "confirmed"
    PLAUSIBLE = "plausible"
    SPECULATIVE = "speculative"
    CONTRADICTED = "contradicted"


class ResearchQuestion(BaseModel):
    """The top-level scientific question under investigation.

    Carries domain context and user-supplied constraints to guide hypothesis generation.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    question: str
    domain: str = ""
    constraints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class FalsificationProtocol(BaseModel):
    """A structured protocol describing how a hypothesis could be experimentally falsified.

    Per 🔴 Speculative convention, every hypothesis tagged SPECULATIVE without an
    accompanying falsification protocol is routed to the graveyard.
    """

    experiment_design: str
    predicted_outcome: str
    key_assumptions: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    """A scientific citation with NLI verification metadata.

    The ``hash`` field stores SHA256(DOI + chunk_text + timestamp) per convention.
    ``nli_label`` stores the NLI verdict (entailment/contradiction/neutral) from the
    grounding agent.
    """

    doi: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    claim_excerpt: str = ""
    nli_label: str = ""
    hash: str = ""


class Hypothesis(BaseModel):
    """A single scientific hypothesis produced by any agent pool.

    Carries its epistemic status, supporting/contradicting citations, an optional
    falsification protocol, and an embedding vector used by the embedding-hull
    diversity filter.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    statement: str
    rationale: str = ""
    confidence: float = 0.0
    epistemic_tag: EpistemicTag = EpistemicTag.SPECULATIVE
    supporting_citations: list[Citation] = Field(default_factory=list)
    contradicting_citations: list[Citation] = Field(default_factory=list)
    falsification_protocol: FalsificationProtocol | None = None
    embedding: list[float] | None = None
    cost: float = 0.0
    generated_by: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class DebateTurn(BaseModel):
    """A single argument turn in a pro/con debate simulation."""

    speaker: str
    argument: str
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class DebateTranscript(BaseModel):
    """A full debate transcript for a hypothesis, tracking pro/con turns and outcome."""

    hypothesis_id: str
    turns: list[DebateTurn] = Field(default_factory=list)
    winner: str = ""
    summary: str = ""


class ReagentItem(BaseModel):
    """A reagent or consumable item needed for a wet-lab feasibility assessment."""

    name: str
    quantity: str = ""
    estimated_cost_usd: float = 0.0
    supplier: str = ""


class FeasibilityReport(BaseModel):
    """Wet-lab feasibility assessment for a single hypothesis.

    Produced by the Feasibility agent pool. The ``go_no_go`` flag is a binary
    recommendation; the final decision may incorporate cost/timeline/risk trade-offs.
    """

    hypothesis_id: str
    overall_feasibility: float = 0.0
    estimated_timeline_weeks: int = 0
    estimated_cost_usd: float = 0.0
    required_reagents: list[ReagentItem] = Field(default_factory=list)
    required_equipment: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    go_no_go: bool = False


class AxisScore(BaseModel):
    """A single-axis score within the MCDA tournament rubric."""

    axis: str
    score: float = 0.0
    rationale: str = ""


class TournamentResult(BaseModel):
    """Ranking output from the Meta-Reasoning tournament round.

    Combines per-axis MCDA scores with a user-supplied weight vector to produce
    a final weighted score and rank.
    """

    hypothesis_id: str
    rank: int = 0
    axis_scores: list[AxisScore] = Field(default_factory=list)
    weighted_score: float = 0.0
    user_weight_vector: dict[str, float] = Field(default_factory=dict)


def merge_dicts(a: dict[Any, Any], b: dict[Any, Any]) -> dict[Any, Any]:
    """Reducer for LangGraph's Annotated type — merges dict b into dict a.

    Used so that ``debates`` and ``feasibility_reports`` accumulate across nodes
    rather than being replaced. Later writes win on key collisions.
    """
    return {**a, **b}


class OpenHypothesisState(BaseModel):
    """Root LangGraph state carrying all data through the discovery pipeline.

    Uses Annotated reducers so that list fields accumulate (``operator.add``) and
    dict fields merge (``merge_dicts``) across nodes. This lets each agent node
    append its output without clobbering prior work.
    """

    question: ResearchQuestion
    stage: str = "init"
    regeneration_cycles: int = 0

    hypotheses: Annotated[list[Hypothesis], operator.add] = Field(default_factory=list)
    graveyard: Annotated[list[Hypothesis], operator.add] = Field(default_factory=list)
    debates: Annotated[dict[str, DebateTranscript], merge_dicts] = Field(default_factory=dict)
    feasibility_reports: Annotated[dict[str, FeasibilityReport], merge_dicts] = Field(
        default_factory=dict
    )
    tournament_results: Annotated[list[TournamentResult], operator.add] = Field(
        default_factory=list
    )

    total_cost_usd: float = 0.0
