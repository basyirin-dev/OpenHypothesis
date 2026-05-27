from typing import Any

from langgraph.types import Command

from openhypothesis.agents.graph_builder import compile_graph
from openhypothesis.state.schema import OpenHypothesisState, ResearchQuestion


class Discover:
    def __init__(self, question: str, domain: str = "") -> None:
        self._question = ResearchQuestion(question=question, domain=domain)
        self._graph = compile_graph()

    async def execute(self, resume: str | None = None) -> OpenHypothesisState:
        initial = OpenHypothesisState(question=self._question)
        thread = {"configurable": {"thread_id": self._question.id}}

        if resume is not None:
            result = await self._graph.ainvoke(Command(resume=resume), thread)
        else:
            result = await self._graph.ainvoke(initial, thread)

        return result  # type: ignore[no-any-return]

    @property
    def question(self) -> ResearchQuestion:
        return self._question

    def get_graph(self) -> Any:
        return self._graph
