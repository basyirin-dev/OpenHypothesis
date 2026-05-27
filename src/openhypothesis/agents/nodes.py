from typing import Any

from openhypothesis.state.schema import (
    DebateTranscript,
    DebateTurn,
    EpistemicTag,
    FalsificationProtocol,
    FeasibilityReport,
    Hypothesis,
    OpenHypothesisState,
    TournamentResult,
)


async def generate_node(state: OpenHypothesisState) -> dict[str, Any]:
    h = Hypothesis(
        statement=f"Generated hypothesis for: {state.question.question[:80]}",
        generated_by="exploration",
        confidence=0.5,
    )
    return {"hypotheses": [h]}


async def regenerate_node(state: OpenHypothesisState) -> dict[str, Any]:
    new_hypotheses: list[Hypothesis] = []
    for h in state.hypotheses:
        if (
            h.epistemic_tag == EpistemicTag.SPECULATIVE
            and h.falsification_protocol is None
        ):
            revised = h.model_copy(deep=True)
            revised.statement = f"(Revised) {h.statement}"
            revised.falsification_protocol = FalsificationProtocol(
                experiment_design="TBD — revision pass",
                predicted_outcome="TBD",
            )
            new_hypotheses.append(revised)
    return {
        "hypotheses": new_hypotheses,
        "regeneration_cycles": state.regeneration_cycles + 1,
    }


async def filter_node(state: OpenHypothesisState) -> dict[str, Any]:
    seen: set[str] = set()
    unique: list[Hypothesis] = []
    for h in state.hypotheses:
        key = h.statement.strip().lower()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(h)
    return {"hypotheses": unique}


async def ground_node(state: OpenHypothesisState) -> dict[str, Any]:
    tagged: list[Hypothesis] = []
    for h in state.hypotheses:
        if h.epistemic_tag == EpistemicTag.SPECULATIVE:
            tagged.append(
                h.model_copy(
                    update={"epistemic_tag": EpistemicTag.PLAUSIBLE},
                    deep=True,
                )
            )
        else:
            tagged.append(h)
    return {"hypotheses": tagged}


async def graveyard_node(state: OpenHypothesisState) -> dict[str, Any]:
    surviving: list[Hypothesis] = []
    discarded: list[Hypothesis] = []
    for h in state.hypotheses:
        if (
            h.epistemic_tag == EpistemicTag.SPECULATIVE
            and h.falsification_protocol is None
        ):
            discarded.append(h)
        else:
            surviving.append(h)
    return {"hypotheses": surviving, "graveyard": discarded}


async def debate_node(state: OpenHypothesisState) -> dict[str, Any]:
    debates: dict[str, DebateTranscript] = {}
    for h in state.hypotheses:
        if h.id not in state.debates:
            debates[h.id] = DebateTranscript(
                hypothesis_id=h.id,
                turns=[
                    DebateTurn(
                        speaker="pro",
                        argument=f"Supporting argument for: {h.statement[:100]}",
                    ),
                    DebateTurn(
                        speaker="con",
                        argument=f"Counterargument for: {h.statement[:100]}",
                    ),
                ],
                winner="pro",
                summary="Stub debate summary.",
            )
    return {"debates": debates}


async def feasibility_node(state: OpenHypothesisState) -> dict[str, Any]:
    reports: dict[str, FeasibilityReport] = {}
    for h in state.hypotheses:
        if h.id not in state.feasibility_reports:
            reports[h.id] = FeasibilityReport(
                hypothesis_id=h.id,
                overall_feasibility=0.7,
                estimated_timeline_weeks=12,
                estimated_cost_usd=5000.0,
                go_no_go=True,
            )
    return {"feasibility_reports": reports}


async def rank_node(state: OpenHypothesisState) -> dict[str, Any]:
    from langgraph.types import interrupt

    interrupt("Ready to run the tournament? This is the most expensive step.")

    results: list[TournamentResult] = []
    for i, h in enumerate(state.hypotheses):
        results.append(
            TournamentResult(
                hypothesis_id=h.id,
                rank=i + 1,
                weighted_score=h.confidence,
            )
        )
    return {
        "tournament_results": results,
        "stage": "done",
    }
