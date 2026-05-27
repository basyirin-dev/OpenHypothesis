from openhypothesis.state.schema import (
    AxisScore,
    Citation,
    DebateTranscript,
    DebateTurn,
    EpistemicTag,
    FalsificationProtocol,
    FeasibilityReport,
    Hypothesis,
    OpenHypothesisState,
    ReagentItem,
    ResearchQuestion,
    TournamentResult,
    merge_dicts,
)


def test_research_question_defaults() -> None:
    rq = ResearchQuestion(question="Is P = NP?")
    assert rq.question == "Is P = NP?"
    assert rq.domain == ""
    assert rq.constraints == []
    assert rq.id != ""


def test_research_question_with_domain() -> None:
    rq = ResearchQuestion(question="Test", domain="mathematics", constraints=["finite"])
    assert rq.domain == "mathematics"
    assert rq.constraints == ["finite"]


def test_hypothesis_defaults() -> None:
    h = Hypothesis(statement="Gravity is a myth")
    assert h.statement == "Gravity is a myth"
    assert h.confidence == 0.0
    assert h.epistemic_tag == EpistemicTag.SPECULATIVE
    assert h.falsification_protocol is None
    assert h.supporting_citations == []
    assert h.id != ""


def test_hypothesis_with_falsification() -> None:
    fp = FalsificationProtocol(
        experiment_design="Drop a ball",
        predicted_outcome="It falls",
    )
    h = Hypothesis(
        statement="Test",
        epistemic_tag=EpistemicTag.SPECULATIVE,
        falsification_protocol=fp,
    )
    assert h.falsification_protocol is not None
    assert h.falsification_protocol.experiment_design == "Drop a ball"


def test_epistemic_tag_values() -> None:
    assert EpistemicTag.CONFIRMED.value == "confirmed"
    assert EpistemicTag.PLAUSIBLE.value == "plausible"
    assert EpistemicTag.SPECULATIVE.value == "speculative"
    assert EpistemicTag.CONTRADICTED.value == "contradicted"


def test_citation() -> None:
    c = Citation(doi="10.1234/test", title="A Test Paper", year=2024)
    assert c.doi == "10.1234/test"
    assert c.hash == ""


def test_debate_transcript() -> None:
    dt = DebateTranscript(hypothesis_id="h1")
    assert dt.hypothesis_id == "h1"
    assert dt.turns == []
    assert dt.winner == ""

    dt2 = DebateTranscript(
        hypothesis_id="h1",
        turns=[DebateTurn(speaker="pro", argument="Good point")],
        winner="pro",
    )
    assert len(dt2.turns) == 1
    assert dt2.turns[0].speaker == "pro"


def test_feasibility_report() -> None:
    r = FeasibilityReport(
        hypothesis_id="h1",
        overall_feasibility=0.85,
        go_no_go=True,
    )
    assert r.overall_feasibility == 0.85
    assert r.go_no_go is True
    assert r.required_reagents == []


def test_reagent_item() -> None:
    ri = ReagentItem(name="CRISPR-Cas9", quantity="10 µg", estimated_cost_usd=250.0)
    assert ri.name == "CRISPR-Cas9"
    assert ri.estimated_cost_usd == 250.0


def test_tournament_result() -> None:
    tr = TournamentResult(
        hypothesis_id="h1",
        rank=1,
        axis_scores=[AxisScore(axis="novelty", score=0.9)],
        weighted_score=0.85,
    )
    assert tr.rank == 1
    assert len(tr.axis_scores) == 1
    assert tr.axis_scores[0].axis == "novelty"
    assert tr.weighted_score == 0.85


def test_merge_dicts() -> None:
    a = {"x": 1, "y": 2}
    b = {"y": 3, "z": 4}
    result = merge_dicts(a, b)
    assert result == {"x": 1, "y": 3, "z": 4}

    assert merge_dicts({}, {}) == {}


def test_open_hypothesis_state_defaults() -> None:
    rq = ResearchQuestion(question="Test")
    state = OpenHypothesisState(question=rq)
    assert state.question.question == "Test"
    assert state.stage == "init"
    assert state.hypotheses == []
    assert state.graveyard == []
    assert state.debates == {}
    assert state.feasibility_reports == {}
    assert state.tournament_results == []
    assert state.total_cost_usd == 0.0
    assert state.regeneration_cycles == 0


def test_open_hypothesis_state_with_hypotheses() -> None:
    rq = ResearchQuestion(question="Test")
    h1 = Hypothesis(statement="H1")
    h2 = Hypothesis(statement="H2")
    state = OpenHypothesisState(
        question=rq,
        hypotheses=[h1, h2],
        total_cost_usd=0.05,
    )
    assert len(state.hypotheses) == 2
    assert state.total_cost_usd == 0.05
