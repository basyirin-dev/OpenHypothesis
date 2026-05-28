# openhypothesis-opencode

OpenCode integration for [OpenHypothesis](https://github.com/basyirin/OpenHypothesis) — agents, commands, MCP server, skills, and lifecycle hooks.

## Installation

```bash
pip install openhypothesis-opencode
```

Requires Python 3.12+ and [OpenCode](https://opencode.ai) installed separately.

## Usage

### Initialise a project

```bash
cd your-research-project
openhypothesis-opencode init
```

This creates:

- `.opencode/agents/scientific-researcher.md` — multi-role discovery agent
- `.opencode/skills/hypothesis-generation/SKILL.md` — diverging gen skill
- `.opencode/skills/wet-lab-feasibility/SKILL.md` — feasibility skill
- `.opencode/skills/literature-review/SKILL.md` — literature review skill
- `.opencode/plugins/openhypothesis.js` — lifecycle hooks
- `opencode.json` — project-level config with agents, commands, and MCP

### Register the MCP server globally

```bash
openhypothesis-opencode setup-mcp
```

This adds the OpenHypothesis MCP server entries to `~/.config/opencode/opencode.json`.

### Restart OpenCode

After initialising or setting up MCP, **quit and restart OpenCode** for the changes to take effect.

## What you get

### Commands

| Command | Description |
|---|---|
| `/discover` | Run the full discovery pipeline on a research question |
| `/ground` | Ground a hypothesis against the Qdrant corpus |
| `/feasibility` | Assess wet-lab feasibility of a protocol |
| `/graveyard` | Search negative results for a target |
| `/audit` | Export a provenance audit trail |
| `/dashboard` | Launch the Gradio web UI |

### MCP Tools

- `search_papers` — semantic paper search
- `check_citation` — citation hash verification
- `check_feasibility` — LLM-based feasibility analysis
- `search_negative_results` — failed experiment lookup
- `generate_hypothesis` — LLM-based hypothesis generation
- `generate_audit_trail` — provenance export

## Development

```bash
cd tools/openhypothesis-opencode
uv sync --group dev
uv run ruff check .
uv run mypy src/
uv run pytest
```

## Publishing

```bash
cd tools/openhypothesis-opencode
uv build
uv publish
```
