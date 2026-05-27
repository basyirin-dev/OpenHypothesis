---
description: Run full validation suite (ruff, mypy, pytest)
agent: build
subtask: true
---

Run the full validation suite in order:

1. `uv run ruff check .` — linting
2. `uv run mypy src/` — type checking
3. `uv run pytest` — tests with coverage

If any step fails, report the error and fix it before proceeding to the next step.
