.PHONY: up down test lint check ingest clean logs shell

up:
	docker compose up -d

down:
	docker compose down

test:
	uv run pytest

lint:
	uv run ruff check . && uv run mypy src/

check: lint
	uv run pytest

ingest:
	uv run python -m openhypothesis.tools.ingest

clean:
	docker compose down -v
	rm -rf duckdb_data/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true

logs:
	docker compose logs -f

shell:
	uv run python
