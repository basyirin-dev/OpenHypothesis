# OpenHypothesis

**A transparent, open-source framework for AI-driven scientific discovery.**

OpenHypothesis is a multi-agent system that generates, grounds, debates, and ranks scientific hypotheses. Built entirely with open-weight LLMs and open-source infrastructure, it provides full inspectability — every ranking decision is a dot product the user can see and change.

## Architecture

Five specialized agent pools orchestrated by LangGraph:

| Pool | Role |
|---|---|
| **Exploration** | Divergent hypothesis generation with temperature annealing (T=1.4 → 0.3) |
| **Adversarial** | Contrarian seeding, embedding-hull diversity enforcement |
| **Grounding** | Tri-layer epistemic tagging (🟢🟡🔴), NLI citation verification |
| **Feasibility** | Wet-lab cost/reagent/timeline JSON reports |
| **Meta-Reasoning** | 7-axis MCDA rubric × user-adjustable weight vector |

## Status

Pre-implementation. Design docs are complete; code scaffolding is in progress. See [Roadmap](OpenHypothesis%20Roadmap.md) for the full build plan.

## Quick Start (once built)

```python
from openhypothesis import Discover

result = await Discover(question="What novel mechanisms could reverse liver fibrosis?").execute()
print(result.top_hypotheses)
```

## License

Apache 2.0
