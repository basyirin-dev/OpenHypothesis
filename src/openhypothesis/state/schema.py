import operator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class EpistemicTag(StrEnum):
    CONFIRMED = "confirmed"
    PLAUSIBLE = "plausible"
    SPECULATIVE = "speculative"
    CONTRADICTED = "contradicted"


class ResearchQuestion(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    question: str
    domain: str = ""
    constraints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class FalsificationProtocol(BaseModel):
    experiment_design: str
    predicted_outcome: str
    key_assumptions: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    doi: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    claim_excerpt: str = ""
    nli_label: str = ""
    hash: str = ""


class Hypothesis(BaseModel):
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
    speaker: str
    argument: str
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class DebateTranscript(BaseModel):
    hypothesis_id: str
    turns: list[DebateTurn] = Field(default_factory=list)
    winner: str = ""
    summary: str = ""


class ReagentItem(BaseModel):
    name: str
    quantity: str = ""
    estimated_cost_usd: float = 0.0
    supplier: str = ""


class FeasibilityReport(BaseModel):
    hypothesis_id: str
    overall_feasibility: float = 0.0
    estimated_timeline_weeks: int = 0
    estimated_cost_usd: float = 0.0
    required_reagents: list[ReagentItem] = Field(default_factory=list)
    required_equipment: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    go_no_go: bool = False


class AxisScore(BaseModel):
    axis: str
    score: float = 0.0
    rationale: str = ""


class TournamentResult(BaseModel):
    hypothesis_id: str
    rank: int = 0
    axis_scores: list[AxisScore] = Field(default_factory=list)
    weighted_score: float = 0.0
    user_weight_vector: dict[str, float] = Field(default_factory=dict)


def merge_dicts(a: dict[Any, Any], b: dict[Any, Any]) -> dict[Any, Any]:
    return {**a, **b}


class OpenHypothesisState(BaseModel):
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
