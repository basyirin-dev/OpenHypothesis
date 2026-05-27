This is the definitive, engineering-grade roadmap to build **OpenHypothesis**, the open-source, multi-agent scientific discovery framework. It is structured into **13 comprehensive phases** (Phase 0 through Phase 12), breaking down the architecture into actionable tasks and subtasks. 

This roadmap assumes a modern Python stack, utilizing **OpenCode** (the AI-powered terminal IDE) for accelerated development, and is designed for a team of 2-4 core engineers or a highly motivated solo developer.

---

### **Phase 0: Bootstrap & OpenCode Environment Setup**
*Goal: Establish the AI-assisted development environment, configure OpenCode to understand the project context, and initialize the repository.*

*   **Task 0.1: Install and Configure OpenCode**
    *   *Subtask 0.1.1:* Install OpenCode CLI (`go install github.com/opencode-ai/opencode@latest` or via `npm`/`brew` depending on the specific fork/distribution).
    *   *Subtask 0.1.2:* Configure local LLM provider for OpenCode (e.g., point to a local Ollama instance running `qwen2.5-coder:32b` or use a BYOK provider like Anthropic/OpenAI for the coding assistant).
    *   *Subtask 0.1.3:* Create the `.opencode/` configuration directory and define the `system_prompt.md` to enforce project conventions (e.g., "Always use Pydantic V2, type hints, and `uv` for dependency management").
*   **Task 0.2: Repository Initialization**
    *   *Subtask 0.2.1:* Initialize Git repository and create the foundational branch structure (`main`, `dev`, `feature/*`).
    *   *Subtask 0.2.2:* Generate the initial `README.md`, `LICENSE` (Apache 2.0 or MIT), and `.gitignore` using OpenCode.
    *   *Subtask 0.2.3:* Initialize the Python project using `uv` (e.g., `uv init openhypothesis`, `uv add pydantic langgraph litellm`).
*   **Task 0.3: Context & Memory Seeding for OpenCode**
    *   *Subtask 0.3.1:* Feed the "OpenHypothesis Architecture Proposal" (from the previous prompt) into OpenCode's context/memory so it understands the 5 Agent Pools and the 7-axis rubric.
    *   *Subtask 0.3.2:* Define OpenCode custom commands (e.g., `/create-agent`, `/write-test`) in the config to standardize code generation.

---

### **Phase 1: Core Infrastructure & Repo Skeleton**
*Goal: Build the foundational software engineering plumbing, CI/CD, and containerization.*

*   **Task 1.1: Monorepo Directory Structure**
    *   *Subtask 1.1.1:* Scaffold directories: `src/openhypothesis/` (core logic), `agents/` (pool implementations), `tools/` (retrieval, parsing), `ui/` (interfaces), `tests/`, `evals/`.
    *   *Subtask 1.1.2:* Set up `pyproject.toml` with strict dependency groups (`dev`, `ui`, `eval`, `local-llm`).
*   **Task 1.2: Containerization & Local Dev Environment**
    *   *Subtask 1.2.1:* Write a comprehensive `docker-compose.yml` spinning up: Qdrant (Vector DB), DuckDB/Postgres (Relational/State), and Redis (Task Queue/Caching).
    *   *Subtask 1.2.2:* Create a `Makefile` or `justfile` for common commands (`make up`, `make test`, `make ingest`).
*   **Task 1.3: CI/CD Pipeline (GitHub Actions)**
    *   *Subtask 1.3.1:* Implement `ruff` for lightning-fast linting and formatting.
    *   *Subtask 1.3.2:* Implement `mypy` for strict static type checking.
    *   *Subtask 1.3.3:* Set up `pytest` with coverage reporting, running automatically on PRs.

---

### **Phase 2: Model Abstraction & BYOK/BYOM Layer**
*Goal: Allow users to Bring Your Own Key (API) or Bring Your Own Model (Local weights) seamlessly.*

*   **Task 2.1: Unified Routing via LiteLLM**
    *   *Subtask 2.1.1:* Integrate `litellm` to standardize calls across OpenAI, Anthropic, Gemini, Groq, and Together AI.
    *   *Subtask 2.1.2:* Implement a `ModelRouter` class that handles fallbacks, rate-limit retries, and token-cost tracking.
*   **Task 2.2: Local Model Integration (BYOM)**
    *   *Subtask 2.2.1:* Add native support for **Ollama** (for consumer hardware).
    *   *Subtask 2.2.2:* Add native support for **vLLM** and **llama.cpp** (for high-throughput local inference).
    *   *Subtask 2.2.3:* Implement an automated model-capability checker (e.g., verifying if the local model supports tool calling or long context).
*   **Task 2.3: Configuration & Secret Management**
    *   *Subtask 2.3.1:* Build a YAML-based config system (`config.yaml`) for defining model profiles (e.g., `exploration_model: qwen2.5-72b`, `grounding_model: llama3.1-8b`).
    *   *Subtask 2.3.2:* Integrate `pydantic-settings` to securely load API keys from `.env` or environment variables without hardcoding.

---

### **Phase 3: State Management & Orchestration Engine**
*Goal: Build the "Supervisor" that manages the multi-agent DAG (Directed Acyclic Graph) using LangGraph.*

*   **Task 3.1: State Schema Definition**
    *   *Subtask 3.1.1:* Define Pydantic models for `ResearchQuestion`, `Hypothesis`, `DebateTranscript`, `FeasibilityReport`, and `TournamentResult`.
    *   *Subtask 3.1.2:* Create the master `OpenHypothesisState` TypedDict/Pydantic model that gets passed through the LangGraph nodes.
*   **Task 3.2: LangGraph Topology Design**
    *   *Subtask 3.2.1:* Define the core nodes: `generate`, `debate`, `ground`, `evaluate_feasibility`, `rank`.
    *   *Subtask 3.2.2:* Implement conditional edges (e.g., if `epistemic_tag == "Speculative"` and `falsification_protocol == None`, route back to `generate`).
*   **Task 3.3: Checkpointing & Human-in-the-Loop (HITL)**
    *   *Subtask 3.3.1:* Integrate LangGraph's `SqliteSaver` or `PostgresSaver` for state persistence (allowing users to pause and resume multi-day runs).
    *   *Subtask 3.3.2:* Implement HITL interrupt nodes where the system pauses and asks the user to approve the research direction before spending compute on the tournament.

---

### **Phase 4: Knowledge Base & Retrieval Pipeline**
*Goal: Build the hard-grounded retrieval engine with cryptographic citation locking.*

*   **Task 4.1: Data Ingestion & Chunking**
    *   *Subtask 4.1.1:* Write ETL scripts to pull metadata and abstracts from OpenAlex, PubMed, and bioRxiv APIs.
    *   *Subtask 4.1.2:* Implement a scientific PDF parser (using `marker` or `nougat`) to extract full-text from Open Access papers.
    *   *Subtask 4.1.3:* Chunk text using semantic chunking (respecting section headers like "Methods" vs "Discussion").
*   **Task 4.2: Vector Database & Embeddings**
    *   *Subtask 4.2.1:* Set up Qdrant collections with appropriate HNSW index parameters for scientific text.
    *   *Subtask 4.2.2:* Integrate open-source embedding models (`BGE-M3` or `nomic-embed-text`) via local inference or API.
*   **Task 4.3: Cryptographic Citation Locking**
    *   *Subtask 4.3.1:* Implement the `CitationHasher` tool: `SHA256(DOI + chunk_text + retrieval_timestamp)`.
    *   *Subtask 4.3.2:* Ensure all downstream agents must pass the valid hash when referencing a claim, preventing "citation drift" or hallucination.

---

### **Phase 5: Exploration & Adversarial Pools (Generation)**
*Goal: Generate highly diverse, novel hypotheses and prevent echo chambers.*

*   **Task 5.1: Divergent Generation Engine**
    *   *Subtask 5.1.1:* Implement temperature-annealed sampling (start at T=1.4, decay to T=0.3 across rounds).
    *   *Subtask 5.1.2:* Create prompt templates that force the LLM to output structured JSON (Hypothesis, Mechanism, Expected Outcome).
*   **Task 5.2: Embedding-Hull Diversity Filter**
    *   *Subtask 5.2.1:* Implement a mathematical function using `scipy.spatial.ConvexHull` to calculate the volume of the generated hypotheses in embedding space.
    *   *Subtask 5.2.2:* Write the logic to trigger the Adversarial Pool if the hull volume shrinks below threshold $\tau$.
*   **Task 5.3: Adversarial "Red Team" Agent**
    *   *Subtask 5.3.1:* Design system prompts for the Contrarian Agent, injecting historical paradigm shifts and retracted papers as few-shot examples.
    *   *Subtask 5.3.2:* Implement the "Wildcard Injection" mechanism that forces the main agents to debate at least one fringe hypothesis per round.

---

### **Phase 6: Grounding & Verification Pool**
*Goal: Epistemic tagging, hallucination detection, and uncertainty quantification.*

*   **Task 6.1: Tri-Layer Epistemic Tagger**
    *   *Subtask 6.1.1:* Build the classification logic to tag claims as 🟢 Grounded, 🟡 Extrapolated, or 🔴 Speculative.
    *   *Subtask 6.1.2:* Implement the rule: "If 🔴 Speculative, a Falsification Protocol JSON object MUST be generated."
*   **Task 6.2: NLI (Natural Language Inference) Verifier**
    *   *Subtask 6.2.1:* Integrate a lightweight NLI model (e.g., `DeBERTa-v3-large` fine-tuned on SciFact) to act as the deterministic claim-verifier.
    *   *Subtask 6.2.2:* Build an ensemble disagreement checker (run verification on 2 different models; if they disagree, flag for human review).
*   **Task 6.3: Uncertainty Quantification**
    *   *Subtask 6.3.1:* Integrate `lm-polygraph` to compute Semantic Entropy over the generated claims.
    *   *Subtask 6.3.2:* Map entropy scores to confidence intervals displayed in the final output.

---

### **Phase 7: Feasibility & "Graveyard" Pools**
*Goal: Ground theoretical ideas in wet-lab reality and historical negative results.*

*   **Task 7.1: Wet-Lab Feasibility Agent**
    *   *Subtask 7.1.1:* Define the strict JSON schema for `FeasibilityReport` (reagents, cost, timeline, biosafety, equipment).
    *   *Subtask 7.1.2:* Build API connectors to Addgene (plasmids), Sigma-Aldrich (reagents), and protocols.io to fetch real-world pricing and availability.
    *   *Subtask 7.1.3:* Implement the "Lab Profile Matcher" that parses a user's uploaded CSV inventory and flags missing equipment.
*   **Task 7.2: The "Graveyard" (Negative Results) Agent**
    *   *Subtask 7.2.1:* Ingest negative-result databases (ClinicalTrials.gov terminated studies, PubChem inactive assays, OSF null results).
    *   *Subtask 7.2.2:* Implement the semantic search query that runs *before* finalization to find prior failed attempts on the same target.
    *   *Subtask 7.2.3:* Auto-generate the "What Has Already Failed" appendix for every surviving hypothesis.

---

### **Phase 8: Tournament & Meta-Reasoning Engine**
*Goal: Simulate scientific debates and rank hypotheses transparently.*

*   **Task 8.1: Multi-Agent Debate Simulation**
    *   *Subtask 8.1.1:* Implement a turn-based dialogue manager where Agent A (Proponent) and Agent B (Skeptic) debate a hypothesis.
    *   *Subtask 8.1.2:* Implement a "Meta-Reviewer" agent that summarizes the debate and extracts concessions/refutations.
*   **Task 8.2: 7-Axis MCDA (Multi-Criteria Decision Analysis) Rubric**
    *   *Subtask 8.2.1:* Code the scoring functions for the 7 axes (Novelty, Groundedness, Falsifiability, Feasibility, Impact, Diversity, Risk-Reward).
    *   *Subtask 8.2.2:* Implement the user-weight vector $\mathbf{w}$ and the dot-product final score calculation ($s = \mathbf{w} \cdot \text{scores}$).
*   **Task 8.3: ELO Rating & Pairwise Comparison**
    *   *Subtask 8.3.1:* Implement an ELO rating system (like Chatbot Arena) for hypotheses to rank them dynamically as debates conclude.

---

### **Phase 9: Interpretability, Audit & Transparency Layer**
*Goal: Ensure the system is a "glass box," not a black box.*

*   **Task 9.1: Provenance & Audit Logging**
    *   *Subtask 9.1.1:* Set up a local DuckDB instance to log every LLM prompt, response, token count, latency, and tool call.
    *   *Subtask 9.1.2:* Create an "Audit Trail" exporter that generates a comprehensive PDF/HTML report of *how* the final hypothesis was reached.
*   **Task 9.2: Counterfactual Explanations**
    *   *Subtask 9.2.1:* Build the logic to compare the #1 and #2 ranked hypotheses.
    *   *Subtask 9.2.2:* Generate natural language counterfactuals (e.g., "Hypothesis A won because of Feasibility. If you reduce the Feasibility weight by 0.2, Hypothesis B wins").
*   **Task 9.3: Interpretability Hooks (Advanced)**
    *   *Subtask 9.3.1:* Integrate `TransformerLens` or `sae-lens` for local models to extract attention patterns and feature activations during the ranking phase.
    *   *Subtask 9.3.2:* Render these activations as heatmaps in the UI.

---

### **Phase 10: User Interfaces (CLI, Web, SDK)**
*Goal: Make the system accessible to bioinformaticians, PIs, and AI engineers.*

*   **Task 10.1: Python SDK**
    *   *Subtask 10.1.1:* Design a clean, pythonic API: `from openhypothesis import Discover; run = Discover(question="...").execute()`.
    *   *Subtask 10.1.2:* Ensure full async support (`asyncio`) for parallel agent execution.
*   **Task 10.2: Rich Terminal CLI**
    *   *Subtask 10.2.1:* Build a CLI using `Typer` and `Rich` to display live-updating tables, progress bars, and agent debate streams in the terminal.
*   **Task 10.3: Gradio / Streamlit Web Dashboard**
    *   *Subtask 10.3.1:* Build the "Control Room" UI: Input research question, adjust the 7-axis weight sliders, and select models.
    *   *Subtask 10.3.2:* Build the "Tournament View" UI: Visualize the embedding hull, read debate transcripts, and inspect epistemic tags (🟢🟡🔴).
    *   *Subtask 10.3.3:* Build the "Lab Profile" upload portal for CSV inventory matching.

---

### **Phase 11: Evaluation, Benchmarking & Red-Teaming**
*Goal: Prove the system works, is safe, and doesn't hallucinate dangerously.*

*   **Task 11.1: Automated Evaluation Harness**
    *   *Subtask 11.1.1:* Create a benchmark dataset of 50 historical scientific breakthroughs (e.g., CRISPR, mRNA vaccines) and 50 known dead-ends.
    *   *Subtask 11.1.2:* Write evaluation scripts to measure if OpenHypothesis ranks the true breakthrough mechanisms higher than the dead-ends.
*   **Task 11.2: Hallucination & Safety Red-Teaming**
    *   *Subtask 11.2.1:* Run adversarial prompts designed to force the system to generate dangerous dual-use research (e.g., gain-of-function pathogens).
    *   *Subtask 11.2.2:* Implement guardrails (e.g., `llama-guard` or NeMo Guardrails) to block the generation of biosecurity threats.
*   **Task 11.3: Performance & Cost Profiling**
    *   *Subtask 11.3.1:* Build a dashboard tracking API costs, local GPU VRAM usage, and time-to-completion per hypothesis.

---

### **Phase 12: Documentation, Community & v1.0 Launch**
*Goal: Prepare the repository for public consumption, contributions, and viral open-source growth.*

*   **Task 12.1: Comprehensive Documentation**
    *   *Subtask 12.1.1:* Set up `MkDocs` with Material theme.
    *   *Subtask 12.1.2:* Write "Quickstart" (5 mins), "Architecture Deep Dive", "BYOK/BYOM Guide", and "Adding Custom Agents" tutorials.
*   **Task 12.2: Community Infrastructure**
    *   *Subtask 12.2.1:* Create `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and standardized GitHub Issue/PR templates.
    *   *Subtask 12.2.2:* Set up a Discord or Matrix server for real-time community support and agent-prompt sharing.
*   **Task 12.3: v1.0 Launch Strategy**
    *   *Subtask 12.3.1:* Record a high-quality 3-minute YouTube/Loom demo showing the system solving a novel biology problem.
    *   *Subtask 12.3.2:* Draft launch posts for HackerNews, Reddit (r/MachineLearning, r/bioinformatics), and X/Twitter.
    *   *Subtask 12.3.3:* Publish an accompanying technical report on arXiv detailing the OpenHypothesis architecture and benchmark results.

---

### **Project Management & Execution Advice**

1.  **AI-Assisted Development:** Use OpenCode (Phase 0) relentlessly. Have it write the Pydantic models, the LangGraph state definitions, and the boilerplate for the LiteLLM router. *Do not write boilerplate by hand.*
2.  **Iterative Checkpoints:** Do not build the whole graph before testing. Build Phase 2 (Models) and Phase 5 (Generation) first. Get a single agent generating hypotheses. Then add Phase 6 (Grounding). Then Phase 8 (Debate).
3.  **Prompt Version Control:** Treat agent system prompts like code. Store them in a dedicated `prompts/` directory, version them, and use a tool like Promptfoo to test them against edge cases.
4.  **Compute Strategy:** For local testing (BYOM), use quantized models (e.g., Qwen2.5-72B-Instruct-AWQ or Llama-3.1-8B). Save the massive 400B+ parameter models for the final v1.0 benchmark runs.