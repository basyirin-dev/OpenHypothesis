"""LangGraph agent node stubs for the OpenHypothesis discovery pipeline.

Each async function in this module is a LangGraph node: it receives the current
``OpenHypothesisState`` and returns a dict of fields to update (merged via
Annotated reducers defined in ``state/schema.py``).

NOTE: These are stub implementations intended for topology validation and CI.
Real implementations should be swapped in once the corresponding agent pool modules
(``agents/exploration/``, ``agents/grounding/``, etc.) are completed.
"""

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
    """Exploration pool stub: produce a single hypothesis from the research question.

    TODO(#phase-5): Replace with ``agents/exploration/generator.py`` which should
    call the LLM via ``ModelRouter`` with temperature annealing (1.4 → 0.3).
    """
    h = Hypothesis(
        statement=f"Generated hypothesis for: {state.question.question[:80]}",
        generated_by="exploration",
        confidence=0.5,
    )
    return {"hypotheses": [h]}


async def regenerate_node(state: OpenHypothesisState) -> dict[str, Any]:
    """Add falsification protocols to speculative hypotheses that lack them.

    Triggered by ``route_after_ground`` when speculative hypotheses without
    falsification protocols survive past the maximum regeneration cycle count.
    """
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
    """Deduplicate hypotheses by statement text (case-insensitive, first 80 chars).

    TODO(#phase-5): Replace with proper embedding-hull diversity filter using Qdrant.
    """
    seen: set[str] = set()
    unique: list[Hypothesis] = []
    for h in state.hypotheses:
        key = h.statement.strip().lower()[:80]
        if key not in seen:
            seen.add(key)
            unique.append(h)
    return {"hypotheses": unique}


async def ground_node(state: OpenHypothesisState) -> dict[str, Any]:
    """Grounding pool stub: upgrade speculative hypotheses to plausible.

    TODO(#phase-6): Replace with ``agents/grounding/tagger.py`` which should
    perform NLI citation verification and assign epistemic tags per the
    tri-layer (🟢🟡🔴) system.
    """
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
    """Discard speculative hypotheses that lack falsification protocols.

    Surviving hypotheses are those that are either non-speculative or have a
    falsification protocol attached. Discarded hypotheses move to the graveyard
    for later analysis.
    """
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
    """Adversarial pool stub: generate a pro/con debate transcript per hypothesis.

    TODO(#phase-7): Replace with ``agents/adversarial/debater.py`` which should
    simulate multi-turn debate with citation-backed arguments.
    """
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
    """Feasibility pool stub: produce a wet-lab feasibility report per hypothesis.

    TODO(#phase-8): Replace with ``agents/feasibility/estimator.py`` which should
    query reagent pricing databases and produce detailed cost/timeline JSON reports.
    """
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
    """Meta-Reasoning pool stub: rank hypotheses with a human-in-the-loop gate.

    Inserts an ``interrupt`` before the expensive tournament round so the user
    can review and approve before proceeding.

    TODO(#phase-9): Replace with ``agents/meta_reasoning/tournament.py`` which
    should compute 7-axis MCDA scores and apply user weight vectors.
    """
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
