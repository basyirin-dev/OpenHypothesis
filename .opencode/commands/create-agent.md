---
description: Scaffold a new agent pool with prompt, module, and tests
agent: build
---

Scaffold a new agent pool named "$ARGUMENTS" in this OpenHypothesis project.

1. Create `agents/<name>/__init__.py` with a Pydantic model class for the agent's output schema.
2. Create `agents/<name>/prompts/<name>.md` with the system prompt (version-controlled, following the prompts/ convention).
3. Create `src/openhypothesis/agents/<name>.py` with the LangGraph node function (async, JSON-in/JSON-out, Pydantic-validated).
4. Create `tests/test_agents/test_<name>.py` with at least one pytest test.

Follow the conventions from AGENTS.md: strict type hints, Pydantic v2, async by default.
