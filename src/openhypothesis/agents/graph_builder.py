"""LangGraph DAG topology for the OpenHypothesis discovery pipeline.

The pipeline flows through 8 agent nodes with two conditional branches:

1. **Regeneration loop**: after grounding, speculative hypotheses without
   falsification protocols may be sent back for revision (up to 3 cycles).
   Those that still lack protocols after the limit are sent to the graveyard.
2. **Graveyard early exit**: if all hypotheses are discarded, the pipeline ends
   early without debating or ranking.
"""

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

# Maximum number of revision cycles for speculative hypotheses without
# falsification protocols. Chosen to balance iteration depth against cost;
# each cycle invokes the LLM per hypothesis.
MAX_REGENERATION_CYCLES = 3


def route_after_ground(state: OpenHypothesisState) -> Literal["regenerate", "graveyard", "debate"]:
    """Decide the next node after grounding based on speculation status.

    - If any speculative hypothesis lacks a falsification protocol **and**
      regeneration cycles remain → send back to ``regenerate``.
    - If any speculative hypothesis still lacks a protocol but cycles are
      exhausted → send to ``graveyard``.
    - Otherwise → proceed to ``debate``.
    """
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
    """Decide the next node after the graveyard.

    If any hypotheses remain → proceed to ``debate``.
    If all were discarded → end the pipeline (no point debating an empty set).
    """
    if state.hypotheses:
        return "debate"
    return "__end__"


def build_graph() -> Any:
    """Construct the LangGraph ``StateGraph`` with all nodes and edges.

    Nodes are added as references to functions in ``agents/nodes.py``.
    Conditional edges implement the regeneration loop and graveyard exit.
    """
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
    """Build and compile the graph with an automatic checkpointer.

    The checkpointer is selected via ``create_checkpointer()`` (Memory, SQLite,
    or Postgres depending on environment config).
    """
    builder = build_graph()
    checkpointer = create_checkpointer()
    graph = builder.compile(checkpointer=checkpointer)
    return graph
