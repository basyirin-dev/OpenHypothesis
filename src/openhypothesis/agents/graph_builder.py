from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from openhypothesis.agents.nodes import (
    debate_node,
    feasibility_node,
    filter_node,
    generate_node,
    graveyard_node,
    ground_node,
    rank_node,
    regenerate_node,
)
from openhypothesis.state.checkpoint import create_checkpointer
from openhypothesis.state.schema import EpistemicTag, OpenHypothesisState

MAX_REGENERATION_CYCLES = 3


def route_after_ground(state: OpenHypothesisState) -> Literal["regenerate", "graveyard", "debate"]:
    needs_fix = any(
        h.epistemic_tag == EpistemicTag.SPECULATIVE and h.falsification_protocol is None
        for h in state.hypotheses
    )
    if needs_fix and state.regeneration_cycles < MAX_REGENERATION_CYCLES:
        return "regenerate"
    if needs_fix:
        return "graveyard"
    return "debate"


def route_after_graveyard(state: OpenHypothesisState) -> Literal["debate", "__end__"]:
    if state.hypotheses:
        return "debate"
    return "__end__"


def build_graph() -> Any:
    builder = StateGraph(OpenHypothesisState)

    builder.add_node("generate", generate_node)
    builder.add_node("regenerate", regenerate_node)
    builder.add_node("filter", filter_node)
    builder.add_node("ground", ground_node)
    builder.add_node("graveyard", graveyard_node)
    builder.add_node("debate", debate_node)
    builder.add_node("feasibility", feasibility_node)
    builder.add_node("rank", rank_node)

    builder.add_edge(START, "generate")
    builder.add_edge("generate", "filter")
    builder.add_edge("filter", "ground")

    builder.add_conditional_edges("ground", route_after_ground)
    builder.add_conditional_edges("graveyard", route_after_graveyard)

    builder.add_edge("debate", "feasibility")
    builder.add_edge("feasibility", "rank")
    builder.add_edge("rank", END)

    return builder


def compile_graph() -> Any:
    builder = build_graph()
    checkpointer = create_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
    return graph
