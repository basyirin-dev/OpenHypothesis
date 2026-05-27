---
description: Deep-dive into architecture — locate agent pools, rubric, or state
agent: plan
---

Search the codebase for "$ARGUMENTS" and provide a detailed summary of how it's implemented.

Start by searching for:
- Agent pool: look in `agents/`, `src/openhypothesis/agents/`
- Rubric/score: look in `src/openhypothesis/scoring/`, `src/openhypothesis/meta_reasoning/`
- State/schema: look in `src/openhypothesis/state/`, `src/openhypothesis/schemas/`
- LangGraph graph definition: look in `src/openhypothesis/graph/`

Return: file paths, key classes/functions, and how it fits into the DAG.
