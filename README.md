# OpenHypothesis

**A transparent, open-source framework for AI-driven scientific discovery.**

OpenHypothesis is a multi-agent system that generates, grounds, debates, and ranks scientific hypotheses. Built entirely with open-weight LLMs and open-source infrastructure, it provides full inspectability — every ranking decision is a dot product the user can see and change.

## Quick Start

```python
from openhypothesis import Discover

result = await Discover(
    question="What novel mechanisms could reverse liver fibrosis?",
    models={"exploration": "local/qwen3", "grounding": "local/gemma3"}
).execute()

print(result.top_hypotheses)
```

## Architecture

Five specialized agent pools orchestrated by LangGraph:

| Pool | Role | Model |
|---|---|---|
| **Exploration** | Divergent hypothesis generation with temperature annealing (T=1.4 → 0.3) | Qwen3-235B-A22B |
| **Adversarial** | Contrarian seeding, embedding-hull diversity enforcement | Llama-4-Maverick (LoRA) |
| **Grounding** | Tri-layer epistemic tagging (🟢🟡🔴), ensemble NLI verification | Gemma-3-27B + Phi-4 |
| **Feasibility** | Wet-lab cost, reagent, equipment, and timeline analysis | DeepSeek-V3 (LoRA) |
| **Meta-Reasoning** | 7-axis MCDA rubric × user-adjustable weight vector | Mistral-Large-2 |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete system design, component specifications, deployment modes, and integration contracts.

## Status

**Phases 0–3 complete**, Phase 4 in progress. See [Roadmap](OpenHypothesis%20Roadmap.md) for the full 15-phase build plan through v1.0 launch.

## OpenCode Integration

OpenHypothesis ships with deep OpenCode ecosystem integration:

| Integration | Location |
|---|---|
| Scientific discovery agent | `.opencode/agents/scientific-researcher.md` |
| Custom commands (`/discover`, `/ground`, `/feasibility`, `/graveyard`, `/audit`, `/dashboard`) | `.opencode/commands/` |
| MCP server (`openhypothesis-mcp`) | `tools/openhypothesis_mcp/` |
| Skills modules (hypothesis generation, feasibility, lit review) | `skills/` |
| Plugin package (`openhypothesis-opencode`) | PyPI |

## Key Features

- **Temperature-annealed exploration** — Systematic exploration of hypothesis space with controlled convergence
- **Cryptographic citation locking** — SHA256 hashing prevents citation drift and hallucination
- **Negative-result awareness** — Graveyard Agent surfaces prior failures before any new experiment
- **Lab inventory integration** — Upload a CSV; the system flags missing equipment and suggests collaborations
- **Transparent ranking** — 7-axis MCDA with user-adjustable weights; every score is visible
- **Counterfactual explanations** — "A beat B because Feasibility (+3.2). If you lower Feasibility weight by 0.2, B wins."
- **Full audit trail** — Every LLM prompt, response, token, and routing decision logged to DuckDB
- **Deterministic mode** — Seeded RNG for fully reproducible discovery sessions
- **Plugin system** — Register custom agent pools, scoring axes, and retrieval backends
- **Air-gapped mode** — Run entirely offline with local models and no external API calls

## License

Apache 2.0
