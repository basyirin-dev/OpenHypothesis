# AGENTS.md — OpenHypothesis

**Phase:** Pre-implementation (design docs only). No code exists yet.

## Stack & Conventions

- **Language:** Python 3.12+
- **Package manager:** `uv` (not pip/poetry)
- **Models:** Pydantic v2 (`BaseModel`, `Field`, `model_validator`)
- **Type hints:** Strict — every function/class must be fully annotated
- **Linting/formatting:** `ruff`
- **Static analysis:** `mypy` (strict mode)
- **Tests:** `pytest` with coverage
- **CI:** GitHub Actions (ruff → mypy → pytest)

## Key Dependencies (from roadmap)

- `langgraph` — multi-agent DAG orchestration
- `litellm` — model routing / BYOK / BYOM
- `qdrant-client` — vector DB (local via Docker)
- `duckdb` — state/audit storage
- `rich` + `typer` — CLI
- `gradio` or `streamlit` — web dashboard
- `transformers`, `vllm`, `ollama` — local inference
- `lm-polygraph` — uncertainty quantification
- `transformerlens`, `sae-lens` — interpretability

## Architecture

**5 agent pools** orchestrated by LangGraph:

| Pool | Role |
|---|---|
| Exploration | Divergent hypothesis generation (T=1.4 → 0.3 annealing) |
| Adversarial | Contrarian seeding, diversity enforcement via embedding hull |
| Grounding | Epistemic tagging (🟢🟡🔴), NLI citation verification |
| Feasibility | Wet-lab cost/reagent/timeline JSON reports |
| Meta-Reasoning | 7-axis MCDA rubric × user weight vector |

**Workflow:** Exploration → Embedding-Hull Filter → Grounding → Graveyard → Adversarial → Feasibility → Meta-Reasoning

**Directory layout:**
```
src/openhypothesis/   — core logic
agents/               — pool implementations
tools/                — retrieval, parsing, citation hashing
ui/                   — CLI + web interfaces
tests/
evals/
prompts/              — version-controlled system prompts
```

## Git Branch Convention

- `main` — stable releases
- `dev` — integration branch
- `feature/<name>` — feature work (branched from `dev`)
- `fix/<name>` — bugfixes (branched from `dev`)

## Dev Environment

- **Container services:** Qdrant + DuckDB/Postgres + Redis (`docker-compose.yml`)
- **Makefile** or `justfile` for common commands (`make up`, `make test`, `make ingest`)
- **Config:** YAML (`config.yaml`) for model profiles; `.env` for secrets via `pydantic-settings`

## Key Conventions

- Store agent prompts in `prompts/` as version-controlled files
- Treat scientific citations with `SHA256(DOI + chunk_text + timestamp)` hashing
- Every 🔴 Speculative claim MUST have an accompanying falsification protocol JSON
- State persisted via LangGraph's `SqliteSaver` / `PostgresSaver`
- Human-in-the-loop interrupt nodes before expensive tournament rounds

## Build Order (recommended in roadmap)

1. Phase 2 (Model abstraction / LiteLLM) + Phase 5 (Generation)
2. Phase 6 (Grounding / verification)
3. Phase 8 (Debate / ranking)
4. Then rest in dependency order

---

## System Instructions

These rules govern all code written for OpenHypothesis:

1. **No boilerplate by hand.** Delegate Pydantic models, LangGraph state definitions, and LiteLLM router scaffolding to the agent — do not hand-write glue code.
2. **Prompt-as-code.** Every agent system prompt lives in `prompts/` as a version-controlled file. Never inline prompts in Python strings across modules.
3. **Validate before commit.** Run `ruff check . && mypy src/ && pytest` (in that order) before any commit or PR. Lint and typecheck must pass.
4. **One agent pool at a time.** Build and test each pool in isolation before wiring it into the LangGraph DAG. Start with Generation (Phase 5), then Grounding (Phase 6), then Debate (Phase 8).
5. **Async by default.** All I/O-bound agent calls, retrieval, and tool execution must use `asyncio`. The SDK entrypoint (`from openhypothesis import Discover`) must support `await`.
6. **JSON in, JSON out.** Every agent output is a validated Pydantic model. Never return raw strings from agent nodes — parse into structured schemas at the boundary.
7. **Quantized for local test.** Default to AWQ/GPTQ quantized models for CI and local dev. Reserve dense 400B+ models for final benchmark runs.

## MCP Tools Usage

| Tool | When to use in this project |
|---|---|
| **arxiv-latex** | Fetch full LaTeX source of papers cited in `grounding/` tests or referenced in feasibility reagent lookups. Prefer this over scholar-mcp when you need precise equation/proof extraction. |
| **context7** | Resolve and query docs for library API questions (LangGraph, LiteLLM, Qdrant, etc.). Always call `resolve-library-id` first, then `query-docs` with the task-specific question. |
| **duckduckgo-mcp-server** | General web search for current bioinformatics tooling, reagent pricing updates, open-access policy changes, or any question the offline docs cannot answer. |
| **github-mcp-server** | Repo management: create/update files, manage issues/PRs, search code across reference repos (langgraph, litellm, qdrant) for usage patterns to mirror. |
| **memory** | Persist cross-session knowledge about architectural decisions, model quirks, and what has been built vs. planned in each phase. Call `create_entities` at phase start, `add_observations` as decisions are made. |
| **puppeteer** | Scrape interactive web UIs (Gradio/Streamlit dashboards, model cards on Hugging Face, reagent vendor catalogs) that lack a REST API. |
| **scholar-mcp** | Primary research literature tool: search papers, get citations/references, download PDFs and extract text. Use for building the grounding corpus, finding negative-result datasets, and verifying citation claims. |
| **sequential-thinking** | Break down complex multi-step architecture problems (e.g., "design the LangGraph topology") before writing code. Use when the design space is large and premature commitment risks rework. |
