---
description: Run ruff and mypy checks
agent: build
subtask: true
---

Run `uv run ruff check .` and `uv run mypy src/` and report any issues found. Fix them.
