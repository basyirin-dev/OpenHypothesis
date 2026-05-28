from typing import Any

from langgraph.types import Command

from openhypothesis.agents.graph_builder import compile_graph
from openhypothesis.state.schema import OpenHypothesisState, ResearchQuestion


class Discover:
    """Async SDK entrypoint for the OpenHypothesis discovery pipeline.

    Usage::

        result = await Discover(question="Is P = NP?").execute()

    The pipeline is a LangGraph DAG. For human-in-the-loop resumption after an
    interrupt node (e.g. ranking), pass the interrupt value to ``execute(resume=...)``.
    """

    def __init__(self, question: str, domain: str = "") -> None:
        """Initialize a discovery run.

        Args:
            question: The scientific question to investigate.
            domain: Optional domain label (e.g. \"mathematics\", \"biology\").
        """
        self._question = ResearchQuestion(question=question, domain=domain)
        try:
            self._graph = compile_graph()
        except Exception as exc:
            raise RuntimeError(
                f"Failed to compile the LangGraph pipeline: {exc}"
            ) from exc

    async def execute(self, resume: str | None = None) -> OpenHypothesisState:
        """Run the full discovery pipeline.

        Args:
            resume: If provided, resumes execution from a prior interrupt
                (e.g. after the human-in-the-loop ranking gate). The value
                is what was passed to ``interrupt()`` in the node.

        Returns:
            The final ``OpenHypothesisState`` containing all hypotheses,
            transcripts, and results.
        """
        initial = OpenHypothesisState(question=self._question)
        thread = {"configurable": {"thread_id": self._question.id}}

        try:
            if resume is not None:
                result = await self._graph.ainvoke(Command(resume=resume), thread)
            else:
                result = await self._graph.ainvoke(initial, thread)
        except Exception as exc:
            raise RuntimeError(
                f"Pipeline execution failed at stage '{initial.stage}': {exc}"
            ) from exc

        return result  # type: ignore[no-any-return]

    @property
    def question(self) -> ResearchQuestion:
        """The ``ResearchQuestion`` this discovery run was created for."""
        return self._question

    def get_graph(self) -> Any:
        """Return the compiled LangGraph for introspection or serialization."""
        return self._graph
