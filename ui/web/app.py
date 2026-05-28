"""Gradio web interface for the OpenHypothesis discovery pipeline.

Usage::

    uv run python -m ui.web.app
"""

from __future__ import annotations

from typing import Any

import gradio as gr

from openhypothesis import Discover
from openhypothesis.state.schema import EpistemicTag

TAG_EMOJI: dict[EpistemicTag, str] = {
    EpistemicTag.CONFIRMED: "\U0001f7e2",
    EpistemicTag.PLAUSIBLE: "\U0001f7e1",
    EpistemicTag.SPECULATIVE: "\U0001f534",
    EpistemicTag.CONTRADICTED: "\u26d4",
}

TAG_LABEL: dict[EpistemicTag, str] = {
    EpistemicTag.CONFIRMED: "Grounded",
    EpistemicTag.PLAUSIBLE: "Extrapolated",
    EpistemicTag.SPECULATIVE: "Speculative",
    EpistemicTag.CONTRADICTED: "Contradicted",
}

MCDA_AXES = [
    "Novelty",
    "Groundedness",
    "Falsifiability",
    "Feasibility",
    "Impact",
    "Diversity",
    "Risk-Reward",
]

_TABLE_HEAD = """<table class="oh-table">
<thead><tr>
<th>Rank</th>
<th>Hypothesis</th>
<th>Status</th>
<th>Confidence</th>
<th>Score</th>
<th>Feasibility</th>
</tr></thead><tbody>"""


def _hypothesis_row(h: Any, rank: int, score: float, feasibility: float | None) -> str:
    """Build a single HTML table row for a hypothesis."""
    emoji = TAG_EMOJI.get(h.epistemic_tag, "\u2753")
    label = TAG_LABEL.get(h.epistemic_tag, "Unknown")
    statement = h.statement[:150] + ("..." if len(h.statement) > 150 else "")
    conf = f"{h.confidence:.2f}" if h.confidence else "-"
    score_str = f"{score:.4f}" if score else "-"
    feas = f"{feasibility:.2f}" if feasibility is not None else "-"
    return (
        f"<tr>"
        f"<td>{rank}</td>"
        f"<td>{statement}</td>"
        f"<td><span class=\"tag tag-{h.epistemic_tag.value}\">{emoji} {label}</span></td>"
        f"<td>{conf}</td>"
        f"<td>{score_str}</td>"
        f"<td>{feas}</td>"
        f"</tr>"
    )


def _build_results_html(state: Any, error: str | None = None) -> str:
    """Render the discovery results as an HTML table."""
    if error:
        return f"""<div class="oh-error"><h3>Pipeline Error</h3><pre>{error}</pre></div>"""

    hypotheses = list(state.hypotheses)
    if not hypotheses:
        return """<div class="oh-empty"><p>No hypotheses were generated. Try a different research question.</p></div>"""

    tournament = {r.hypothesis_id: r for r in state.tournament_results}
    feasibility = {r.hypothesis_id: r for r in getattr(state, "feasibility_reports", {}).values()}

    sorted_results = sorted(
        hypotheses,
        key=lambda h: tournament[h.id].weighted_score if h.id in tournament else 0.0,
        reverse=True,
    )

    rows: list[str] = []
    for i, h in enumerate(sorted_results, start=1):
        tr = tournament.get(h.id)
        fr = feasibility.get(h.id)
        rows.append(
            _hypothesis_row(
                h,
                rank=tr.rank if tr else i,
                score=tr.weighted_score if tr else 0.0,
                feasibility=fr.overall_feasibility if fr else None,
            )
        )

    return _TABLE_HEAD + "".join(rows) + "</tbody></table>"


async def run_discovery(
    question: str,
    domain: str,
    _novelty: float,
    _groundedness: float,
    _falsifiability: float,
    _feasibility: float,
    _impact: float,
    _diversity: float,
    _risk_reward: float,
) -> tuple[str, str]:
    """Execute the discovery pipeline and return results HTML and cost summary."""
    if not question.strip():
        return (
            """<div class="oh-empty"><p>Please enter a research question.</p></div>""",
            "",
        )

    try:
        result = await Discover(question=question.strip(), domain=domain.strip()).execute()
    except Exception as exc:
        error_html = _build_results_html(None, error=str(exc))
        return error_html, ""

    results_html = _build_results_html(result)

    cost_summary = _build_cost_summary(result)

    return results_html, cost_summary


def _build_cost_summary(state: Any) -> str:
    """Render cost and metadata summary as markdown."""
    parts: list[str] = []
    parts.append(f"**Total cost:** ${state.total_cost_usd:.6f}")
    parts.append(f"**Stage:** {state.stage}")
    parts.append(f"**Hypotheses:** {len(state.hypotheses)}")
    parts.append(f"**Tournament results:** {len(state.tournament_results)}")
    return " &nbsp;|&nbsp; ".join(parts)


CSS = """
.oh-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.oh-table th {
    text-align: left;
    padding: 8px 12px;
    border-bottom: 2px solid #ddd;
    font-weight: 600;
}
.oh-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #eee;
    vertical-align: top;
}
.oh-table tbody tr:hover {
    background: #f5f5f5;
}
.tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
}
.tag-grounded { background: #d4edda; color: #155724; }
.tag-plausible { background: #fff3cd; color: #856404; }
.tag-speculative { background: #f8d7da; color: #721c24; }
.tag-contradicted { background: #e2e3e5; color: #383d41; }
.oh-empty {
    padding: 40px;
    text-align: center;
    color: #888;
    font-style: italic;
}
.oh-error {
    padding: 20px;
    background: #f8d7da;
    border: 1px solid #f5c6cb;
    border-radius: 6px;
    color: #721c24;
}
.oh-error pre {
    white-space: pre-wrap;
    font-size: 13px;
    margin-top: 8px;
}
"""


def create_app() -> gr.Blocks:
    """Build and return the Gradio Blocks application."""
    with gr.Blocks(
        title="OpenHypothesis",
    ) as demo:
        gr.Markdown(
            "# \U0001f52c OpenHypothesis — Research Dashboard",
        )

        with gr.Row():
            with gr.Column(scale=3):
                question = gr.Textbox(
                    label="Research Question",
                    placeholder="e.g. What epigenetic mechanisms drive neuronal ageing?",
                    lines=2,
                )
                domain = gr.Textbox(
                    label="Domain (optional)",
                    placeholder="biology, chemistry, neuroscience, ...",
                )
                run_btn = gr.Button("Run Discovery", variant="primary", size="lg")

            with gr.Column(scale=2):
                gr.Markdown("### MCDA Weights")
                gr.Markdown(
                    "*Adjustable weights for the seven evaluation axes.*\n"
                    "*Real-time re-ranking will be available in a future release.*",
                )
                sliders: list[gr.Slider] = []
                for axis in MCDA_AXES:
                    slider = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=1.0,
                        step=0.1,
                        label=axis,
                        interactive=False,
                    )
                    sliders.append(slider)

        cost_md = gr.Markdown("")
        results_html = gr.HTML(
            value="""<div class="oh-empty"><p>Submit a research question to begin.</p></div>""",
        )

        run_btn.click(
            fn=run_discovery,
            inputs=[question, domain, *sliders],
            outputs=[results_html, cost_md],
        )

    return demo


demo = create_app()

if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Soft(),
        css=CSS,
    )
