---
description: Generate a pytest test file for a given source module
agent: build
---

Generate a pytest test file for the source module "$ARGUMENTS".

1. Determine the correct path in `tests/` that mirrors the source path.
2. Read the source module to understand its public API (functions, classes).
3. Write tests that cover:
   - Normal/expected usage (happy path)
   - Edge cases (empty input, None, boundary values)
   - Error cases (if applicable)
4. Use `pytest` idioms: fixtures, parametrize, etc.
5. Follow project conventions: strict type hints, async tests where applicable.

Read the existing `tests/test_import.py` for style reference.
