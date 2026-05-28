# OpenHypothesis Roadmap

Definitive engineering roadmap for **OpenHypothesis**, the open-source, multi-agent scientific discovery framework. Structured into **15 phases** (0 through 14), each decomposed into tasks and subtasks.

**Current Status:** 29 May 2026 — Phases 0–3 complete, Phase 4 in progress, Phases 5–14 planned through 30 June 2026.

---

### Phase 0: Bootstrap & OpenCode Environment Setup `[26–27 May]` ✅
*Goal: Establish the AI-assisted development environment, configure OpenCode to understand the project context, and initialize the repository.*

- **Task 0.1: Install and Configure OpenCode**
  - *Subtask 0.1.1:* Install the OpenCode CLI tool.
  - *Subtask 0.1.2:* Configure the local LLM provider for OpenCode (Ollama / LiteLLM).
  - *Subtask 0.1.3:* Create the `.opencode/` configuration directory and define the `system_prompt.md` with project context.
- **Task 0.2: Repository Initialization**
  - *Subtask 0.2.1:* Initialize a Git repository and establish the branch convention (`main`, `dev`, `feature/*`, `fix/*`).
  - *Subtask 0.2.2:* Generate `README.md`, `LICENSE` (Apache 2.0), and `.gitignore`.
  - *Subtask 0.2.3:* Initialize the Python project using `uv` with `pyproject.toml`.
- **Task 0.3: Context and Memory Seeding for OpenCode**
  - *Subtask 0.3.1:* Ingest the OpenHypothesis architecture proposal into OpenCode's persistent memory.
  - *Subtask 0.3.2:* Define OpenCode custom commands in the configuration to standardize code generation workflows.

---

### Phase 1: Core Infrastructure and Repository Skeleton `[27 May]` ✅
*Goal: Build the foundational software engineering plumbing, CI/CD tooling, and containerization.*

- **Task 1.1: Monorepo Directory Structure**
  - *Subtask 1.1.1:* Scaffold the directory tree: `src/openhypothesis/`, `agents/`, `tools/`, `ui/`, `prompts/`, `tests/`, `evals/`, `docs/`.
  - *Subtask 1.1.2:* Configure `pyproject.toml` with strict dependency groups (`dev`, `ui`, `eval`, `local-llm`, `plugin`).
- **Task 1.2: Containerization and Local Development Environment**
  - *Subtask 1.2.1:* Author `docker-compose.yml` defining Qdrant (vector store), PostgreSQL (state persistence), and Redis (caching / rate limiting).
  - *Subtask 1.2.2:* Create a `Makefile` encapsulating common commands (`make up`, `make test`, `make lint`, `make ingest`).
- **Task 1.3: CI/CD Pipeline**
  - *Subtask 1.3.1:* Configure `ruff` for linting and formatting enforcement on every pull request.
  - *Subtask 1.3.2:* Configure `mypy` in strict mode for static type checking across `src/` and `agents/`.
  - *Subtask 1.3.3:* Configure `pytest` with coverage reporting and a minimum threshold gate.

---

### Phase 2: Model Abstraction and BYOK/BYOM Layer `[27 May]` ✅
*Goal: Enable users to bring their own API keys or their own local models through a unified interface.*

- **Task 2.1: Unified Routing via LiteLLM**
  - *Subtask 2.1.1:* Integrate `litellm` as the unified API provider abstraction layer.
  - *Subtask 2.1.2:* Implement the `ModelRouter` class with automatic fallback, rate-limit retry with exponential backoff, and per-request token-cost tracking.
- **Task 2.2: Local Model Integration**
  - *Subtask 2.2.1:* Add native support for **Ollama** (consumer-grade local inference).
  - *Subtask 2.2.2:* Add native support for **vLLM** and **llama.cpp** (high-throughput local inference for server deployments).
  - *Subtask 2.2.3:* Implement an automated model-capability checker that probes tool-calling, function-calling, and context-window limits.
- **Task 2.3: Configuration and Secret Management**
  - *Subtask 2.3.1:* Design a YAML-based configuration system (`config.yaml`) for model profiles, provider credentials, and routing rules.
  - *Subtask 2.3.2:* Integrate `pydantic-settings` for `.env` variable loading with validation.

---

### Phase 3: State Management and Orchestration Engine `[28 May]` ✅
*Goal: Build the supervisory layer that manages the multi-agent directed acyclic graph using LangGraph.*

- **Task 3.1: State Schema Definition**
  - *Subtask 3.1.1:* Define Pydantic models for all core domain entities: `ResearchQuestion`, `Hypothesis`, `DebateTranscript`, `FeasibilityReport`, `TournamentResult`, `AuditRecord`.
  - *Subtask 3.1.2:* Create the master `OpenHypothesisState` with `Annotated` reducers for append-based list fields and merge-based dictionary fields.
- **Task 3.2: LangGraph Topology Design**
  - *Subtask 3.2.1:* Define core graph nodes: `generate`, `regenerate`, `filter`, `ground`, `graveyard`, `debate`, `feasibility`, `rank`.
  - *Subtask 3.2.2:* Implement conditional edges, including finite-cycle regeneration for speculative claims that lack accompanying falsification protocols.
- **Task 3.3: Checkpointing and Human-in-the-Loop**
  - *Subtask 3.3.1:* Integrate `SqliteSaver` for development and `PostgresSaver` for production state persistence.
  - *Subtask 3.3.2:* Implement human-in-the-loop interrupt nodes at critical decision points (before tournament ranking, before final report generation).

---

### Phase 4: Knowledge Base and Retrieval Pipeline `[28–30 May]` 🔄
*Goal: Build the grounded retrieval engine with cryptographic citation locking and scheduled literature updates.*

- **Task 4.1: Data Ingestion and Chunking**
  - *Subtask 4.1.1:* Write ETL scripts to pull metadata and abstracts from OpenAlex, PubMed, bioRxiv, and CrossRef APIs.
  - *Subtask 4.1.2:* Implement a scientific PDF parser (using `marker` or `nougat`) to extract full text from open-access papers.
  - *Subtask 4.1.3:* Chunk text using semantic segmentation that respects document structure (sections, paragraphs, figure captions).
- **Task 4.2: Vector Database and Embeddings**
  - *Subtask 4.2.1:* Configure Qdrant collections with HNSW index parameters optimized for scientific text retrieval.
  - *Subtask 4.2.2:* Integrate open-source embedding models (`BGE-M3`, `nomic-embed-text-v1.5`) via local inference or API endpoint.
- **Task 4.3: Cryptographic Citation Locking**
  - *Subtask 4.3.1:* Implement the `CitationHasher` tool: `SHA256(DOI + chunk_text + retrieval_timestamp)`.
  - *Subtask 4.3.2:* Enforce that all downstream agent outputs must reference valid citation hashes, preventing citation drift and hallucination.
- **Task 4.4: Ingestion Scheduler (NEW)**
  - *Subtask 4.4.1:* Implement a configurable cron-based scheduler (`schedule_ingestion.py`) for daily or weekly literature updates.
  - *Subtask 4.4.2:* Add a `make ingest` command and a `POST /ingest` API endpoint for on-demand re-indexing.

---

### Phase 5: OpenCode-Native Integration `[31 May – 1 Jun]` ⬜
*Goal: Make OpenHypothesis accessible as a first-class OpenCode ecosystem citizen through agents, custom commands, MCP tools, skills, a plugin package, and a standalone Gradio MVP.*

- **Task 5.1: Scientific Discovery OpenCode Agent**
  - *Subtask 5.1.1:* Create `.opencode/agents/scientific-researcher.md` with a system prompt tuned for hypothesis generation, literature grounding, and feasibility analysis.
  - *Subtask 5.1.2:* Register the agent in `opencode.json` with explicit tool permissions (Qdrant read, DuckDB query, Gradio launch) and model defaults.
  - *Subtask 5.1.3:* Implement role-specific temperature profiles (T=1.4 for exploration, T=0.3 for verification and ranking).
- **Task 5.2: Custom OpenCode Commands**
  - *Subtask 5.2.1:* Implement `/discover` — execute the full discovery pipeline on a natural-language research question.
  - *Subtask 5.2.2:* Implement `/ground` — ground a single hypothesis string against the local Qdrant corpus with epistemic tagging.
  - *Subtask 5.2.3:* Implement `/feasibility` — run wet-lab feasibility analysis against a proposed protocol or hypothesis.
  - *Subtask 5.2.4:* Implement `/graveyard` — search the negative-results corpus for prior failed attempts on a given target or mechanism.
  - *Subtask 5.2.5:* Implement `/audit` — export a full provenance audit trail for a previous discovery session.
  - *Subtask 5.2.6:* Implement `/dashboard` — launch the Gradio web UI from the terminal with automatic browser opening.
- **Task 5.3: OpenHypothesis MCP Server**
  - *Subtask 5.3.1:* Build the `openhypothesis-mcp` server exposing tools: `search_papers`, `check_citation`, `check_feasibility`, `search_negative_results`, `generate_hypothesis`, `generate_audit_trail`.
  - *Subtask 5.3.2:* Define JSON Schema input and output specifications for every MCP tool.
  - *Subtask 5.3.3:* Register the MCP server in `opencode.json` with stdio transport for development and SSE transport for production.
  - *Subtask 5.3.4:* Implement per-agent tool access control (e.g., `/audit` available only to the plan agent).
- **Task 5.4: OpenHypothesis Skills Module**
  - *Subtask 5.4.1:* Author `skills/hypothesis-generation/SKILL.md` — methodology for divergent scientific hypothesis generation with temperature annealing.
  - *Subtask 5.4.2:* Author `skills/wet-lab-feasibility/SKILL.md` — reagent pricing, biosafety levels, equipment matching, protocol costing.
  - *Subtask 5.4.3:* Author `skills/literature-review/SKILL.md` — citation verification, epistemic tagging, negative-results mining best practices.
- **Task 5.5: OpenCode Plugin Package**
  - *Subtask 5.5.1:* Create the `openhypothesis-opencode` pip-installable package that registers agents, commands, MCP server, and skills on installation.
  - *Subtask 5.5.2:* Implement plugin lifecycle hooks: `onSessionCreated` (load project context), `onToolExecute` (log queries to DuckDB), `onFileEdited` (re-index changed lab inventories).
  - *Subtask 5.5.3:* Publish to PyPI with OpenCode listed as an optional dependency.
- **Task 5.6: Gradio Standalone Application (MVP)**
  - *Subtask 5.6.1:* Build a minimal Gradio interface: a text input for the research question and a results panel displaying top-10 hypotheses with epistemic tags (🟢🟡🔴).
  - *Subtask 5.6.2:* Add a read-only weight-slider panel for the seven MCDA axes (real-time re-ranking deferred to Phase 11).
  - *Subtask 5.6.3:* Implement the `/dashboard` command binding that launches the Gradio server and opens the browser automatically.

---

### Phase 6: Exploration and Adversarial Pools (Generation) `[2–4 Jun]` ⬜
*Goal: Generate highly diverse, novel hypotheses and prevent echo-chamber convergence through enforced adversarial seeding.*

- **Task 6.1: Divergent Generation Engine**
  - *Subtask 6.1.1:* Implement temperature-annealed sampling: initial rounds at T=1.4, decaying to T=0.3 across successive generations.
  - *Subtask 6.1.2:* Create structured prompt templates that force the LLM to emit constrained JSON (Hypothesis, Mechanism, Expected Outcome, Confidence Interval).
- **Task 6.2: Embedding-Hull Diversity Filter**
  - *Subtask 6.2.1:* Implement a diversity metric using `scipy.spatial.ConvexHull` to compute the volume occupied by surviving hypotheses in embedding space.
  - *Subtask 6.2.2:* Implement the threshold trigger $\tau$: when hull volume contracts below the threshold, the Adversarial Pool is re-invoked with an explicit out-of-hull generation instruction.
- **Task 6.3: Adversarial Red-Team Agent**
  - *Subtask 6.3.1:* Design system prompts for the contrarian agent that incorporate historical paradigm shifts (Kuhn case studies) and retracted-paper corpora as few-shot examples.
  - *Subtask 6.3.2:* Implement the wildcard injection mechanism: one fringe hypothesis per round that the main agents must debate rather than dismiss.
- **Task 6.4: Per-Pool Validation (NEW)**
  - *Subtask 6.4.1:* Write unit tests for the generation engine: temperature accuracy, JSON schema compliance, embedding-hull volume calculation.
  - *Subtask 6.4.2:* Write integration tests for the adversarial injection workflow: verify that the pool produces hypotheses outside the current hull.

---

### Phase 7: Grounding and Verification Pool `[5–7 Jun]` ⬜
*Goal: Epistemic tagging, hallucination detection, uncertainty quantification, and citation verification.*

- **Task 7.1: Tri-Layer Epistemic Tagger**
  - *Subtask 7.1.1:* Build the classification logic to tag claims as 🟢 Grounded (supported by two or more peer-reviewed sources), 🟡 Extrapolated (logically consistent but not directly stated), or 🔴 Speculative (no direct support).
  - *Subtask 7.1.2:* Enforce the rule: every 🔴 Speculative claim must be accompanied by a structured falsification protocol JSON object.
- **Task 7.2: Natural Language Inference Verifier**
  - *Subtask 7.2.1:* Integrate a lightweight NLI model (e.g., `DeBERTa-v3-large` fine-tuned on SciFact) as the primary claim-verification classifier.
  - *Subtask 7.2.2:* Build an ensemble disagreement detector: run verification across two distinct models; if their classifications diverge, flag the claim for human review.
- **Task 7.3: Uncertainty Quantification**
  - *Subtask 7.3.1:* Integrate `lm-polygraph` to compute semantic entropy and eigenvector centrality over generated claim graphs.
  - *Subtask 7.3.2:* Map entropy scores to calibrated confidence intervals displayed alongside every hypothesis.
- **Task 7.4: Per-Pool Validation (NEW)**
  - *Subtask 7.4.1:* Write unit tests for epistemic tagger accuracy, NLI classifier precision/recall, and ensemble agreement rates.
  - *Subtask 7.4.2:* Write integration tests for the full grounding pipeline against a curated gold-standard corpus of 100 claims.

---

### Phase 8: Feasibility and Graveyard Pools `[8–10 Jun]` ⬜
*Goal: Ground theoretical ideas in wet-lab reality, reagent pricing, equipment availability, and historical negative results.*

- **Task 8.1: Wet-Lab Feasibility Agent**
  - *Subtask 8.1.1:* Define the strict JSON schema for `FeasibilityReport`: reagents, cost estimates, timeline, biosafety level, equipment requirements, known failure modes.
  - *Subtask 8.1.2:* Build API connectors to Addgene (plasmid availability and pricing), Sigma-Aldrich (reagent catalog), and protocols.io (published protocols).
  - *Subtask 8.1.3:* Implement the lab profile matcher: parse a user-uploaded CSV inventory and flag missing equipment, reagents, or skills.
- **Task 8.2: Negative-Results (Graveyard) Agent**
  - *Subtask 8.2.1:* Ingest negative-result databases: ClinicalTrials.gov terminated studies, PubChem BioAssay inactive records, OSF registered reports with null outcomes, ChEMBL inactive assays.
  - *Subtask 8.2.2:* Implement the semantic search query executed before hypothesis finalization that retrieves prior failed attempts on the same target or mechanism.
  - *Subtask 8.2.3:* Auto-generate the "What Has Already Failed" appendix appended to every surviving hypothesis.
- **Task 8.3: Per-Pool Validation (NEW)**
  - *Subtask 8.3.1:* Write unit tests for feasibility report schema validation, API connector error handling, and lab-profile parsing.
  - *Subtask 8.3.2:* Write integration tests for the graveyard retrieval accuracy against a manually curated failure database.

---

### Phase 9: Tournament and Meta-Reasoning Engine `[11–12 Jun]` ⬜
*Goal: Simulate structured scientific debates and rank hypotheses transparently using an auditable rubric.*

- **Task 9.1: Multi-Agent Debate Simulation**
  - *Subtask 9.1.1:* Implement a turn-based dialogue manager where Agent A (Proponent) and Agent B (Skeptic) debate a hypothesis across configurable rounds.
  - *Subtask 9.1.2:* Implement a meta-reviewer agent that summarizes each debate and extracts concessions, refutations, and unresolved points.
- **Task 9.2: Seven-Axis MCDA Rubric**
  - *Subtask 9.2.1:* Code the scoring functions for each axis: Novelty, Groundedness, Falsifiability, Feasibility, Impact, Diversity, Risk-Reward.
  - *Subtask 9.2.2:* Implement the user-weight vector $\mathbf{w}$ and the final score computation $s = \mathbf{w} \cdot \text{scores}$ with full auditability.
- **Task 9.3: ELO Rating and Pairwise Comparison**
  - *Subtask 9.3.1:* Implement a dynamic ELO rating system for hypotheses, updated incrementally as each pairwise debate concludes.
- **Task 9.4: Per-Pool Validation (NEW)**
  - *Subtask 9.4.1:* Write unit tests for each of the seven scoring functions, ELO rating calculations, and weight-vector arithmetic.
  - *Subtask 9.4.2:* Write integration tests for the full debate-to-ranking pipeline with synthetic hypothesis sets.

---

### Phase 10: Interpretability, Audit, and Transparency Layer `[13–15 Jun]` ⬜
*Goal: Ensure every decision in the pipeline is fully inspectable, attributable, and explainable.*

- **Task 10.1: Provenance and Audit Logging**
  - *Subtask 10.1.1:* Deploy a local DuckDB instance to record every LLM prompt, response, token count, latency, tool call, and routing decision.
  - *Subtask 10.1.2:* Implement the audit trail exporter that generates a comprehensive PDF and HTML report tracing how each final hypothesis was produced.
- **Task 10.2: Counterfactual Explanations**
  - *Subtask 10.2.1:* Build the logic to compare the top-two ranked hypotheses and attribute the score difference to specific rubric axes.
  - *Subtask 10.2.2:* Generate natural-language counterfactuals: "Hypothesis A won because of Feasibility. If you reduce the Feasibility weight by 0.2, Hypothesis B wins."
- **Task 10.3: Interpretability Hooks**
  - *Subtask 10.3.1:* Integrate `TransformerLens` and `sae-lens` for locally hosted models to extract attention patterns and sparse autoencoder feature activations during ranking.
  - *Subtask 10.3.2:* Render extracted activations as token-attribution heatmaps in the web dashboard.
- **Task 10.4: Backup and Disaster Recovery (NEW)**
  - *Subtask 10.4.1:* Implement automated PostgreSQL dump scheduling (`pg_dump` via cron) with configurable retention policy.
  - *Subtask 10.4.2:* Document the restore procedure and add a `make restore` command.

---

### Phase 11: User Interfaces (Staged) `[16–19 Jun]` ⬜
*Goal: Deliver progressive UI capability — CLI first, then MVP web dashboard, then full-featured application.*

- **Task 11.1: Rich Terminal CLI (available after Phase 6)**
  - *Subtask 11.1.1:* Build a feature-complete CLI using `Typer` with subcommands for each pipeline stage: `discover`, `ground`, `feasibility`, `graveyard`, `audit`.
  - *Subtask 11.1.2:* Integrate `Rich` for live-updating tables, progress bars, and color-coded agent debate streams in the terminal.
  - *Subtask 11.1.3:* Implement output formatting flags (`--json`, `--csv`, `--markdown`) for programmatic consumption.
- **Task 11.2: Gradio Control Room Dashboard (available after Phase 7)**
  - *Subtask 11.2.1:* Build the "Control Room" tab: research question input, MCDA weight sliders (real-time re-ranking), model selection dropdown.
  - *Subtask 11.2.2:* Build the "Tournament View" tab: embedding-hull visualization, debate transcripts, epistemic tag color coding.
  - *Subtask 11.2.3:* Build the "Lab Profile" tab: CSV inventory upload, equipment gap analysis, reagent cost summary.
- **Task 11.3: Full Dashboard Enhancement (available after Phase 10)**
  - *Subtask 11.3.1:* Add the "Audit Trail" tab: provenance graph viewer, token-attribution heatmaps, counterfactual comparison panel.
  - *Subtask 11.3.2:* Add the "History" tab: session browser, cross-session comparison, run reproducibility controls.
  - *Subtask 11.3.3:* Implement user authentication for multi-user deployments (API key or OAuth2).

---

### Phase 12: Fine-Tuning Pipeline `[20–22 Jun]` ⬜
*Goal: Produce specialized LoRA adapters for each agent pool to improve domain-specific performance.*

- **Task 12.1: Fine-Tuning Infrastructure**
  - *Subtask 12.1.1:* Set up a training environment with `Unsloth` or `Axolotl` for efficient LoRA/QLoRA fine-tuning.
  - *Subtask 12.1.2:* Curate training datasets: retracted-paper corpus (Adversarial), protocols.io corpus (Feasibility), SciFact NLI corpus (Grounding).
  - *Subtask 12.1.3:* Implement a training pipeline that can run on a single A100 (24GB VRAM target).
- **Task 12.2: Adversarial Pool Adapter**
  - *Subtask 12.2.1:* Fine-tune Llama-4-Maverick on the retracted-paper and paradigm-shift corpus with LoRA rank=64.
  - *Subtask 12.2.2:* Evaluate adversarial output diversity against a baseline (non-fine-tuned) model.
- **Task 12.3: Feasibility Pool Adapter**
  - *Subtask 12.3.1:* Fine-tune DeepSeek-V3-Lite or Qwen3-30B on protocols.io and Bio-Protocol corpora.
  - *Subtask 12.3.2:* Evaluate feasibility report accuracy against human-annotated protocol cost estimates.
- **Task 12.4: NLI Verifier Adapter**
  - *Subtask 12.4.1:* Fine-tune Phi-4 or Qwen3-4B exclusively on the claim-verification task (SUPPORTS / REFUTES / NEUTRAL / NOT_FOUND).
  - *Subtask 12.4.2:* Evaluate against the SciFact leaderboard benchmark.
- **Task 12.5: Adapter Management and Versioning**
  - *Subtask 12.5.1:* Implement a model registry (local directory or Hugging Face Hub integration) for storing and loading adapters.
  - *Subtask 12.5.2:* Add adapter auto-detection to the `ModelRouter`: if an adapter exists for a given pool, load it automatically.

---

### Phase 13: Evaluation, Benchmarking, and Security `[23–27 Jun]` ⬜
*Goal: Prove system correctness, safety, and performance through rigorous testing against established baselines.*

- **Task 13.1: Automated Evaluation Harness**
  - *Subtask 13.1.1:* Create a benchmark dataset of 50 historical scientific breakthroughs (CRISPR, mRNA vaccines, optogenetics) and 50 known dead-ends.
  - *Subtask 13.1.2:* Write evaluation scripts measuring whether OpenHypothesis ranks true breakthrough mechanisms higher than dead-ends.
  - *Subtask 13.1.3:* Benchmark against Co-Scientist's published results (antimicrobial resistance, plant immunity, liver fibrosis cases).
- **Task 13.2: Hallucination and Safety Red-Teaming**
  - *Subtask 13.2.1:* Run adversarial prompt suites designed to force generation of dangerous dual-use research (gain-of-function, bioweapons).
  - *Subtask 13.2.2:* Implement guardrails (`llama-guard` or NeMo Guardrails) to block biosecurity threats before generation.
  - *Subtask 13.2.3:* Conduct dependency CVE scanning (`pip-audit`, `trivy`) and remediate critical and high-severity vulnerabilities.
- **Task 13.3: Performance and Cost Profiling**
  - *Subtask 13.3.1:* Build a dashboard tracking API costs, local GPU VRAM usage, and wall-clock time per hypothesis.
  - *Subtask 13.3.2:* Implement configurable budget caps (max tokens per session, max API spend per month) with automatic pipeline halt when exceeded.
- **Task 13.4: Per-Pool Regression Suite (NEW)**
  - *Subtask 13.4.1:* Aggregate all per-pool unit and integration tests from Phases 6–9 into a unified regression suite.
  - *Subtask 13.4.2:* Run the full regression suite against every new adapter or model configuration before merge.

---

### Phase 14: Documentation, Community, and v1.0 Launch `[28–30 Jun]` ⬜
*Goal: Prepare the repository for public consumption, community contribution, and open-source growth.*

- **Task 14.1: Comprehensive Documentation**
  - *Subtask 14.1.1:* Deploy `MkDocs` with the Material theme and auto-publish via GitHub Pages.
  - *Subtask 14.1.2:* Write Quickstart Guide (5 minutes), Architecture Deep Dive, BYOK/BYOM Configuration Guide, Adding Custom Agents tutorial, and Plugin Developer Guide.
- **Task 14.2: Community Infrastructure**
  - *Subtask 14.2.1:* Create `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and standardized GitHub Issue and Pull Request templates.
  - *Subtask 14.2.2:* Establish a Discord or Matrix server for community support and agent-prompt sharing.
  - *Subtask 14.2.3:* Create a public benchmark leaderboard for community-submitted hypothesis-generation challenges.
- **Task 14.3: v1.0 Launch Strategy**
  - *Subtask 14.3.1:* Record a high-quality demonstration video (3–5 minutes) showing the system solving a novel biology problem end to end.
  - *Subtask 14.3.2:* Draft launch posts for HackerNews, Reddit (r/MachineLearning, r/bioinformatics), and X/Twitter.
  - *Subtask 14.3.3:* Publish an accompanying technical report on arXiv detailing the OpenHypothesis architecture, benchmark results, and comparison against Co-Scientist.

---

### Project Management and Execution Guidelines

1. **AI-Assisted Development:** Leverage OpenCode for all boilerplate generation — Pydantic models, LangGraph state definitions, LiteLLM router scaffolding. Do not write glue code by hand.
2. **Iterative Checkpoints:** Build and validate each agent pool in isolation before integrating into the full LangGraph DAG. Begin with Generation (Phase 6), then Grounding (Phase 7), then Feasibility (Phase 8).
3. **Prompt Version Control:** Store all system prompts in the `prompts/` directory under version control. Use `promptfoo` or an equivalent tool to test prompts against edge cases.
4. **Compute Strategy:** Default to quantized models (AWQ/GPTQ) for local CI and development. Reserve dense 400B+ parameter models for final v1.0 benchmark runs.
5. **Testing Discipline:** Run `ruff check . && mypy src/ && pytest` before every commit. Lint and typecheck must pass before any merge.
6. **Semantic Versioning:** Adopt `calver` or `semver` for the SDK. Document all breaking changes in a `CHANGELOG.md` and provide migration guides.
