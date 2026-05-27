from langgraph.graph import StateGraph

from openhypothesis.agents.graph_builder import build_graph, compile_graph, route_after_graveyard
from openhypothesis.state.schema import Hypothesis, OpenHypothesisState, ResearchQuestion


def test_build_graph_returns_stategraph() -> None:
    builder = build_graph()
    assert isinstance(builder, StateGraph)


def test_compile_graph_produces_invocable() -> None:
    graph = compile_graph()
    assert graph is not None
    assert hasattr(graph, "ainvoke")


def test_route_after_graveyard_with_hypotheses() -> None:
    rq = ResearchQuestion(question="Test")
    state = OpenHypothesisState(
        question=rq,
        hypotheses=[Hypothesis(statement="A")],
    )
    assert route_after_graveyard(state) == "debate"


def test_route_after_graveyard_empty() -> None:
    rq = ResearchQuestion(question="Test")
    state = OpenHypothesisState(question=rq)
    assert route_after_graveyard(state) == "__end__"
