# OpenHypothesis: A Transparent, Open-Source Framework for Scientific Discovery

**Architecture Document — Version 2.0**

---

## 1. Executive Summary

OpenHypothesis is an open-source, multi-agent framework for AI-driven scientific hypothesis generation, grounding, debate, and ranking. It addresses six structural weaknesses inherent in closed-source scientific discovery systems (opaque ranking, locked training signal, uniform priors, citation-only verification, absence of wet-lab feasibility assessment, and exclusion of negative results) by leveraging open-weight large language models and fully inspectable infrastructure.

The system orchestrates five specialized agent pools through a LangGraph-directed acyclic graph: Exploration (divergent generation with temperature annealing), Adversarial (contrarian seeding and diversity enforcement), Grounding (tri-layer epistemic tagging with cryptographic citation hashing), Feasibility (wet-lab cost and resource analysis), and Meta-Reasoning (interpretable multi-criteria ranking with user-adjustable weights). Every intermediate artifact is persisted to an auditable store, and every ranking decision reduces to a transparent dot product the user can inspect and modify.

OpenHypothesis ships as a standalone Python application with a Gradio web dashboard, a rich terminal CLI, a Python SDK, and deep integration with the OpenCode development ecosystem (custom agents, MCP tools, slash commands, and a pip-installable plugin). It supports single-user desktop deployments, multi-user lab servers, and fully air-gapped offline operation.

---

## 2. Problem Statement

### 2.1 The Replication Crisis and Innovation Deficit

The scientific community faces twin crises: a replication crisis (over 70% of published findings in some fields cannot be reproduced) and an innovation deficit (the cost of drug discovery exceeds \$2.6 billion per approved compound, with clinical trial success rates below 10%). Both problems share a common root: the cognitive and institutional biases embedded in how hypotheses are generated, selected, and tested.

AI systems that assist with hypothesis generation risk amplifying these biases unless their reasoning is transparent, their training signals are adaptable, and their outputs are grounded in verifiable evidence rather than plausibility.

### 2.2 Six Structural Weaknesses of Closed-Source Co-Scientist Systems

| Weakness | Description | Consequence |
|---|---|---|
| **Opaque ranking** | The mechanism by which one hypothesis is preferred over another is hidden inside a proprietary model. | Users cannot audit, contest, or learn from ranking decisions. |
| **Locked training signal** | The model cannot be fine-tuned on a laboratory's private negative results, internal protocols, or niche preprints. | Institutional knowledge remains siloed; the same blind spots apply to every user. |
| **Uniform priors** | Every user receives the same model-flavored worldview, trained on the same public distribution. | Echo-chamber effects are amplified; genuinely heterodox ideas are systematically filtered out. |
| **Citation-only verification** | Verification collapses into "has someone already published this?" | True novelty is implicitly penalized; speculative but promising hypotheses are discarded. |
| **No wet-lab feasibility** | Theoretical elegance is not distinguished from experimental viability. | Resources are wasted on elegant but infeasible proposals. |
| **No negative results** | Training data and retrieval skew toward positive findings. | Researchers unknowingly retest hypotheses already falsified. |

### 2.3 Why Open-Weight Models Solve These Structurally

Open-weight models (Llama 4, Qwen3, DeepSeek-V3, Gemma 3, Mistral-Large-2, OLMo 3) provide four properties that closed APIs cannot:

1. **Inspectability** — Attention patterns, feature activations, and scoring rubrics can be extracted, visualized, and audited.
2. **Fine-tunability** — Any agent pool can be adapted to a laboratory's private data via LoRA without negotiating enterprise contracts.
3. **Composability** — Users can replace, reorder, or extend agent pools, scoring axes, and retrieval backends.
4. **Freedom from API-level opacity** — Every token, every decision, every cost is measurable and attributable.

---

## 3. System Architecture

### 3.1 Overview

OpenHypothesis uses a LangGraph-directed acyclic graph to orchestrate five specialized agent pools. State flows through the graph in a defined pipeline, with conditional edges for regeneration and human-in-the-loop interrupts at critical decision points.

```
User defines research question
         │
         ▼
[Domain-Density Check] ──► sets retrieval mode and epistemic priors
         │
         ▼
[Exploration Pool] ──► N candidate hypotheses (T=1.4, nucleus p=0.99)
         │
         ▼
[Embedding-Hull Filter] ──► prunes to diverse subset
         │
         ▼
[Grounding Pool] ──► tri-layer tags (🟢🟡🔴) + cryptographic citations
         │
         ├──🔴 Speculative without falsification protocol? ──► [Regenerate]
         │
         ▼
[Graveyard Agent] ──► appends prior failures from negative-results corpus
         │
         ▼
[Adversarial Pool] ──► injects contrarian wildcards
         │
         ▼
[Feasibility Pool] ──► structured JSON per hypothesis
         │
         ▼
[Meta-Reasoning Pool] ──► 7-axis MCDA rubric × user-adjustable weight vector
         │
         ▼
[Tournament & Debate] ──► pairwise ELO ranking
         │
         ▼
[HITL Interrupt] ──► human review before finalization
         │
         ▼
Top-N hypotheses with full provenance, counterfactuals, heatmaps
```

### 3.2 Agent Pools

| Pool | Role | Recommended Model | Key Technique |
|---|---|---|---|
| **Exploration** | Divergent hypothesis generation with enforced diversity | Qwen3-235B-A22B | Temperature annealing (T=1.4 → 0.3), nucleus sampling |
| **Adversarial** | Contrarian seeding and paradigm challenge | Llama-4-Maverick | LoRA fine-tuned on retractions + paradigm shifts |
| **Grounding** | Citation verification, epistemic tagging, hallucination detection | Gemma-3-27B + Phi-4 (NLI) | Tri-layer tagging, ensemble disagreement, SHA256 hashing |
| **Feasibility** | Wet-lab reality check (cost, reagents, ethics, timeline) | DeepSeek-V3 | LoRA fine-tuned on protocols.io + Bio-Protocol |
| **Meta-Reasoning** | Transparent ranking with user-tunable rubrics | Mistral-Large-2 | 7-axis MCDA, ELO ranking, counterfactual generation |

All pools are orchestrated by **LangGraph** with state persisted via SqliteSaver (development) or PostgresSaver (production).

### 3.3 LangGraph Topology

The state graph is defined with the following nodes and conditional edges:

- **Nodes:** `domain_density_check`, `generate`, `regenerate`, `filter`, `ground`, `graveyard`, `inject_adversarial`, `feasibility`, `debate`, `rank`, `hitl_review`, `finalize`
- **Conditional edges:** `ground → regenerate` (if any claim is 🔴 Speculative without falsification protocol); `filter → inject_adversarial` (if embedding-hull volume < threshold τ); `rank → hitl_review` (before final output)
- **State schema:** `OpenHypothesisState` with Annotated reducers for list and dictionary fields, defined via Pydantic v2 models.

### 3.4 Core Domain Models

```python
class ResearchQuestion(BaseModel):
    text: str
    domain: str | None = None
    density: Literal["dense", "sparse", "unknown"] = "unknown"

class Claim(BaseModel):
    text: str
    epistemic_status: Literal["grounded", "extrapolated", "speculative"]
    citations: list[CitationHash]
    falsification_protocol: FalsificationProtocol | None = None

class Hypothesis(BaseModel):
    id: UUID
    title: str
    mechanism: str
    claims: list[Claim]
    embedding: list[float]
    dice_scores: dict[str, float]
    final_score: float | None = None

class FeasibilityReport(BaseModel):
    reagents: list[Reagent]
    equipment: list[str]
    estimated_total_cost_usd: float
    timeline_weeks: int
    biosafety_level: int
    ethical_clearance_needed: list[str]
    known_failure_modes: list[str]
    skill_level_required: str

class OpenHypothesisState(BaseModel):
    question: ResearchQuestion
    hypotheses: Annotated[list[Hypothesis], add]
    debate_transcripts: Annotated[list[DebateTranscript], add]
    feasibility_reports: Annotated[dict[str, FeasibilityReport], merge]
    tournament_results: TournamentResult | None = None
    audit_trail: Annotated[list[AuditRecord], add]
```

---

## 4. User Personas and Workflows

### 4.1 Wet-Lab Principal Investigator

**Goal:** Identify testable hypotheses that fit within the laboratory's equipment, budget, and expertise.

**Workflow:**
1. Upload lab inventory CSV (reagents, equipment, personnel skills).
2. Enter a research question: *"What mechanisms could reverse pulmonary fibrosis?"*
3. Adjust MCDA weight sliders — Feasibility set to 0.30, Novelty to 0.15.
4. Review top-10 hypotheses with feasibility reports and "What Has Already Failed" appendices.
5. Click "Generate Audit Trail" for a full PDF provenance report to include in a grant application.

### 4.2 Computational Bioinformatician

**Goal:** Integrate OpenHypothesis into existing analysis pipelines.

**Workflow:**
1. Install `openhypothesis` via pip.
2. Write a Python script:
   ```python
   from openhypothesis import Discover
   result = await Discover(question="...", models={"exploration": "local/qwen3"}).execute()
   for h in result.top_hypotheses:
       print(h.title, h.final_score, [c.text for c in h.claims if c.epistemic_status == "speculative"])
   ```
3. Export results as JSON for downstream processing.

### 4.3 Graduate Student

**Goal:** Explore a new domain, understand the research landscape, and identify promising directions.

**Workflow:**
1. Launch the Gradio dashboard and enter a broad question.
2. Browse the tournament view: read debate transcripts, inspect epistemic tags, and explore the embedding-hull visualization.
3. Click counterfactual explanations to understand why one hypothesis outranks another.
4. Fork a previous session to test a different weight configuration.

### 4.4 Lab Manager

**Goal:** Estimate pre-study costs and resource allocation for competing research directions.

**Workflow:**
1. Upload the current lab inventory and equipment list.
2. Run the feasibility pipeline on a shortlist of candidate projects.
3. Export a cost-comparison matrix: total reagents, lead times, missing equipment, biosafety requirements.
4. Identify collaboration needs (e.g., "cryo-EM required — partner with X lab").

### 4.5 Philosopher of Science / Metascience Researcher

**Goal:** Audit the system's reasoning processes and study how AI-generated hypotheses compare to human-generated ones.

**Workflow:**
1. Access the full DuckDB audit log via an SQL client.
2. Inspect token-attribution heatmaps from the Meta-Reasoning pool's TransformerLens hooks.
3. Compare counterfactual scenarios: what would the system recommend under different epistemic priors?
4. Propose modifications to the MCDA rubric as a research object itself.

---

## 5. Component Specifications

### 5.1 Exploration Pool

The Exploration Pool generates an initial population of candidate hypotheses designed to maximize coverage of the hypothesis space.

**Algorithm:**
1. Retrieve top-\(K\) papers from the Qdrant corpus relevant to the research question.
2. Generate \(N\) hypotheses (configurable, default 200) using the primary generation model.
3. Use temperature-annealed sampling: initial rounds at \(T=1.4, p=0.99\), decaying to \(T=0.3, p=0.90\) across rounds.
4. Each hypothesis is output as structured JSON with four fields: `title`, `mechanism`, `expected_outcome`, `confidence_interval`.

**Diversity constraint:** After each generation round, embed all hypotheses and compute the convex hull volume. If the volume shrinks below threshold \(\tau\), the Adversarial Pool is triggered before the next round.

### 5.2 Adversarial Pool

The Adversarial Pool prevents echo-chamber convergence by deliberately injecting contrarian and heterodox hypotheses.

**Mechanisms:**
1. **Contrarian fine-tuning:** A Llama-4-Maverick instance is fine-tuned via LoRA on a corpus of retracted papers, paradigm-shift case studies, and articles from the *Journal of Controversial Ideas*.
2. **Wildcard injection:** One hypothesis per tournament round is drawn from a "fringe" retrieval queue seeded with low-citation preprints from arXiv and bioRxiv. The main agent pool is forced to debate this hypothesis.
3. **Hull-violation generation:** When the Embedding-Hull Filter detects volume contraction, the Adversarial Pool receives an explicit instruction: *"Generate hypotheses whose embeddings lie outside the current convex hull."*

### 5.3 Grounding Pool

The Grounding Pool assigns every claim an epistemic status and cryptographically locks citations to prevent drift.

**Tri-layer epistemic tagging:**
- 🟢 **Grounded:** Supported by two or more peer-reviewed sources, verified via NLI classifier over full-text PDF content.
- 🟡 **Extrapolated:** Logically consistent with grounded claims but not directly stated in any retrieved source. Uncertainty is quantified via token-level entropy across 32 sampling passes.
- 🔴 **Speculative:** A novel claim with no direct literature support. Automatically penalized in ranking *unless* accompanied by a well-formed falsification protocol.

**Ensemble NLI verification:**
Three distinct NLI models (DeBERTa-v3-large, Phi-4 fine-tuned, Gemma-3-27B) independently classify each claim-citation pair as SUPPORTS, REFUTES, NEUTRAL, or NOT_FOUND. If the ensemble disagrees (non-majority), the claim is auto-flagged for human review.

**Cryptographic citation locking:**
Every citation hash is computed as `SHA256(DOI + chunk_text + retrieval_timestamp)`. The hash is stored alongside the hypothesis. Any downstream modification to the citation text invalidates the hash, providing a tamper-evident chain.

**Domain-density detection:**
Before grounding, the system queries OpenAlex to estimate the publication density of the target subfield. Below a threshold of 100 publications per year, the system auto-switches to high-precision retrieval mode and prepends a system prompt: *"You are operating in a sparsely documented domain. Default to 🟡 Extrapolated or 🔴 Speculative tags. Do not fabricate citations."*

### 5.4 Feasibility Pool

The Feasibility Pool converts theoretical hypotheses into structured wet-lab assessments.

**FeasibilityReport schema:**
```json
{
  "reagents": [
    {
      "name": "Recombinant human TGF-β1",
      "vendor": "R&D Systems",
      "catalog_number": "240-B-010",
      "cost_usd": 425.00,
      "lead_time_days": 7,
      "in_stock": true
    }
  ],
  "equipment": ["confocal microscope", "FACS", "real-time PCR system"],
  "estimated_total_cost_usd": 18500.00,
  "timeline_weeks": 12,
  "biosafety_level": 2,
  "ethical_clearance_needed": ["IACUC"],
  "known_failure_modes": [
    "Antibody X has 40% cross-reactivity per Abcam datasheet",
    "Primary cell line Y shows batch-dependent viability"
  ],
  "skill_level_required": "postdoctoral researcher",
  "missing_equipment": ["cryo-electron microscope"],
  "collaboration_suggestions": ["Partner with Z lab for cryo-EM access"]
}
```

**Lab profile integration:**
Users upload a CSV inventory of their laboratory's reagents, equipment, and personnel skills. The Feasibility cross-references every hypothesis against this inventory, flagging gaps and suggesting collaborations.

**Data sources:**
- Addgene API (plasmid availability and pricing)
- Sigma-Aldrich / Fisher Scientific open catalog APIs (reagent cost and lead time)
- protocols.io (published protocols with step-by-step reagent lists)
- Bio-Protocol (peer-reviewed methods)
- IACUC / IRB public templates (ethics clearance awareness)

### 5.5 Graveyard Agent

The Graveyard Agent searches negative-results databases before a hypothesis is finalized, ensuring that prior failures are surfaced as mandatory context.

**Ingested sources:**
- ClinicalTrials.gov (terminated trials, studies with `study_results = "no"`)
- PubChem BioAssay (~100 million inactive compound data points)
- OSF Registered Reports (null-outcome studies)
- ChEMBL (inactive assay data)
- *Journal of Negative Results in BioMedicine* (archived)
- PLOS ONE null-result papers
- F1000Research registered reports with null outcomes

**Output:**
A "What Has Already Failed" appendix appended to every surviving hypothesis, listing structurally similar hypotheses that were tested and falsified, known off-target effects, and prior failed attempts on the same target.

**Negative-result bonus:**
Hypotheses that explicitly cite and learn from prior negative results receive a bonus on the Groundedness axis during MCDA scoring.

### 5.6 Meta-Reasoning Pool

The Meta-Reasoning Pool produces transparent, auditable rankings.

**Seven-axis MCDA rubric (each scored 0–10):**

| Axis | Definition | Scoring Method |
|---|---|---|
| Novelty | Embedding distance from known literature | Cosine distance to nearest neighbor in Qdrant corpus |
| Groundedness | Proportion of 🟢 claims | Direct count |
| Falsifiability | Quality of proposed falsification experiment | NLI agent scores clarity, specificity, and testability |
| Feasibility | Wet-lab viability | From FeasibilityReport (inverted cost + timeline) |
| Impact Potential | Citation velocity of the subfield | OpenAlex citation trajectory model |
| Diversity | Marginal gain to embedding-hull volume | Volume delta if hypothesis is added vs. excluded |
| Risk-Reward | Speculative-claim ratio × falsification quality | Ratio × NLI falsifiability score |

**Final score:**
\[
s = \mathbf{w} \cdot \text{scores}
\]
where \(\mathbf{w}\) is a user-adjustable weight vector (default: uniform). The entire computation is transparent — every axis score, every weight, and the final dot product are displayed in the UI.

**Counterfactual explanation:**
For any pair (A, B) where A ranked higher, the system auto-generates a structured explanation: *"A beat B because Feasibility (+3.2), Novelty (−1.1), Groundedness (+0.8). If you reduce the Feasibility weight from 0.30 to 0.15, B would have won."*

---

## 6. OpenCode-Native Integration

OpenHypothesis is designed as a first-class citizen of the OpenCode development ecosystem, providing multiple integration points.

### 6.1 Scientific Discovery OpenCode Agent

A project-local OpenCode agent (`scientific-researcher`) pre-configured for hypothesis generation, literature grounding, and feasibility analysis.

**Configuration:** `.opencode/agents/scientific-researcher.md`

```yaml
model: qwen3-235b-instruct
temperature: 0.7
permissions:
  allow:
    - "read"
    - "glob"
    - "grep"
    - "bash"
  ask:
    - "write"
    - "edit"
system_prompt: {file: ./prompts/scientific-researcher/system.md}
```

**Capabilities:**
- Query the local Qdrant knowledge base for relevant literature.
- Generate structured hypotheses with temperature-controlled creativity.
- Run the grounding pipeline against live citation data.
- Launch the Gradio dashboard for interactive exploration.

### 6.2 Custom OpenCode Commands

| Command | Function | Pipeline Stage |
|---|---|---|
| `/discover` | Run the full discovery pipeline | End to end |
| `/ground` | Ground a single hypothesis | Grounding |
| `/feasibility` | Run feasibility analysis on a protocol | Feasibility |
| `/graveyard` | Search negative results for a target | Graveyard |
| `/audit` | Export audit trail for a previous session | Audit |
| `/dashboard` | Launch the Gradio web UI | UI |

Each command is defined as an OpenCode command template in `.opencode/commands/` and backed by the `openhypothesis-mcp` server or direct Python invocation.

### 6.3 OpenHypothesis MCP Server

A Model Context Protocol server (`openhypothesis-mcp`) exposing scientific discovery tools to any MCP-compatible client.

**Exposed tools:**

| Tool | Input | Output | Description |
|---|---|---|---|
| `search_papers` | `query: str`, `limit: int` | `list[Paper]` | Search the local knowledge base |
| `check_citation` | `claim: str`, `paper_id: str` | `VerificationResult` | NLI verification with hash |
| `check_feasibility` | `hypothesis: str`, `inventory: str\|None` | `FeasibilityReport` | Wet-lab analysis |
| `search_negative_results` | `target: str`, `mechanism: str` | `list[FailedAttempt]` | Graveyard lookup |
| `generate_hypothesis` | `question: str`, `temperature: float` | `Hypothesis` | Single hypothesis generation |
| `generate_audit_trail` | `session_id: str` | `AuditTrail` | Full provenance report |

### 6.4 OpenHypothesis Skills Module

Reusable skill files that teach OpenCode agents best practices for scientific workflows:

- `skills/hypothesis-generation/SKILL.md` — Temperature annealing methodology, diversity enforcement, structured output formatting.
- `skills/wet-lab-feasibility/SKILL.md` — Reagent pricing sources, biosafety level classification, equipment requirement estimation.
- `skills/literature-review/SKILL.md` — Citation verification workflow, epistemic tagging criteria, negative-results mining strategy.

### 6.5 OpenCode Plugin Package

The `openhypothesis-opencode` pip-installable package provides:

- Automatic registration of all OpenCode agents, commands, MCP server, and skills.
- Plugin lifecycle hooks for session management (`onSessionCreated`, `onToolExecute`, `onFileEdited`).
- Integration with OpenCode's audit logging (every scientific query is recorded alongside engineering context).

The package is published to PyPI and installable via:
```bash
pip install openhypothesis-opencode
```

### 6.6 Gradio Standalone Application

A self-contained Gradio web application that runs independently of OpenCode, serving as the primary visual interface.

**Tabs:**
1. **Control Room** — Research question input, MCDA weight sliders, model selection, run button.
2. **Tournament View** — Embedding-hull visualization, debate transcripts, epistemic tag color coding.
3. **Lab Profile** — CSV inventory upload, equipment gap analysis, cost summary.
4. **Audit Trail** — Provenance graph, token-attribution heatmaps, counterfactual comparison.
5. **History** — Session browser, cross-session comparison, run reproducibility controls.

Launch command: `openhypothesis dashboard` or via OpenCode `/dashboard`.

---

## 7. Data Privacy and Sovereignty

### 7.1 Encryption Architecture

- **Data at rest:** The local DuckDB audit store and SQLite/Postgres state store are encrypted using AES-256-GCM. Encryption keys are derived from a user-provided passphrase or hardware-bound TPM key.
- **Data in transit:** All inter-service communication (Qdrant gRPC, Postgres wire protocol, Redis) uses TLS 1.3. MCP server communication uses mTLS for production deployments.
- **Model inference data:** When using local (BYOM) models, inference data never leaves the host machine. When using remote API providers, data is encrypted in transit and users are warned about provider data policies.

### 7.2 Regulatory Compliance

- **GDPR:** All user data is portable (exportable as JSON/CSV/PDF) and deletable (a single `DeleteSession` API call purges all associated records).
- **HIPAA:** The system supports a compliance mode that disables all remote API calls (BYOM only), encrypts the DuckDB audit store at rest, and prevents audit logs from being written to disk (memory-only mode).
- **Data retention:** Configurable retention policies with automatic purging of sessions older than a user-specified threshold.

### 7.3 Tenant Isolation

In multi-user deployments:
- Each user (or lab) operates within an isolated namespace.
- Qdrant collections are prefix-scoped per tenant.
- Postgres state store uses row-level security policies.
- The lab-private null-result ledger is never accessible to other tenants.

### 7.4 Lab-Private Null-Result Ledger

Each laboratory can upload its own failed experiments as a private corpus. These entries:
- Are stored locally and never transmitted to any external API.
- Are treated as first-class citations by the Grounding Pool.
- Prevent the lab from re-testing a hypothesis it already falsified internally.
- Are hashed with a lab-specific salt to prevent cross-lab identification.

### 7.5 Data Purging

A `purge` utility removes all artifacts associated with a session or lab:
```bash
openhypothesis purge --session-id <uuid>             # Single session
openhypothesis purge --lab-id <uuid> --older-than 90d  # Batch purge
```

---

## 8. Plugin and Extension System

### 8.1 Agent Plugin Protocol

Third parties can register custom agent pools by implementing the `AgentPlugin` protocol:

```python
class AgentPlugin(Protocol):
    name: str
    async def initialize(self, config: dict) -> None: ...
    async def process(self, state: OpenHypothesisState) -> dict[str, Any]: ...
    def dependencies(self) -> list[str]: ...  # Nodes that must run before this one
```

Plugins are discovered via `pkg_resources` entry points or explicit registration in `config.yaml`. Each plugin runs as a LangGraph node and can read/write the shared state.

### 8.2 Scorer Plugin Protocol

Custom MCDA axes are registered by implementing the `ScorerPlugin` protocol:

```python
class ScorerPlugin(Protocol):
    name: str
    description: str
    min_value: float = 0.0
    max_value: float = 10.0
    async def score(self, hypothesis: Hypothesis, state: OpenHypothesisState) -> float: ...
```

### 8.3 Retriever Plugin Protocol

Custom retrieval backends implement the `RetrieverPlugin` protocol:

```python
class RetrieverPlugin(Protocol):
    name: str
    async def retrieve(self, query: str, k: int = 10) -> list[Document]: ...
    async def index(self, documents: list[Document]) -> int: ...
```

### 8.4 Hook System

Lifecycle hooks allow plugins to observe and modify pipeline execution:

| Hook | Trigger | Payload |
|---|---|---|
| `pre_generation` | Before Exploration Pool runs | ResearchQuestion |
| `post_generation` | After Exploration Pool completes | list[Hypothesis] |
| `pre_grounding` | Before Grounding Pool runs | list[Hypothesis] |
| `post_grounding` | After Grounding Pool completes | list[Hypothesis] |
| `on_error` | Any node raises an exception | Node name, exception, traceback |
| `on_ranking` | After final ranking computed | TournamentResult |

### 8.5 Plugin Discovery and Versioning

- Plugins are installed via pip and registered in `config.yaml` under the `plugins` key.
- Each plugin declares a `plugin_version` and `api_version` for compatibility checking.
- A `--plugins-only` mode allows the system to boot with only specified plugins (for minimal deployments).

---

## 9. Session Management and Reproducibility

### 9.1 Workspace and Project Model

Each discovery session belongs to a **project**, which groups related sessions under a common research topic. Projects have:
- A human-readable name and description.
- A shared lab inventory (inherited by all child sessions).
- A shared MCDA weight template (inherited but overridable).
- Cross-session comparison dashboards.

### 9.2 Deterministic Run Mode

For reproducibility, the system supports a deterministic mode:

```python
result = await Discover(question="...", deterministic=True, seed=42).execute()
```

In deterministic mode:
- All RNG seeds are recorded in the audit trail.
- Model temperatures are locked to 0.0 for verification steps and to the annealed schedule for generation.
- The exact set of retrieved documents is cached and replayed on re-execution.
- Two runs with the same seed and question produce identical outputs.

### 9.3 Session Save, Load, and Fork

- **Save:** Automatically on every node completion (LangGraph checkpointing). Explicit save triggers a named checkpoint.
- **Load:** Restore a previous session from its checkpoint. The system replays only unprocessed nodes.
- **Fork:** Create a new session from any checkpoint with modified parameters (e.g., different MCDA weights). The forked session shares all prior state but diverges from the fork point.

### 9.4 Cross-Session Comparison

The UI supports side-by-side comparison of two or more sessions:
- Compare MCDA score breakdowns.
- Overlay embedding-hull volumes.
- Diff the "What Has Already Failed" appendices.
- Identify hypotheses that survive across different weight configurations (robustness analysis).

### 9.5 Audit Trail Export

Two export formats:
- **PDF:** Formatted report with executive summary, hypothesis cards, debate transcripts, and provenance diagram.
- **HTML:** Interactive report with collapsible sections, searchable content, and embedded visualizations.

Export command: `openhypothesis audit --session-id <uuid> --format pdf --output report.pdf`

---

## 10. Integrated Workflow

```
[1] User defines research question
    │
[2] Domain-density check
    ├── Dense domain (≥100 pubs/yr) → Standard retrieval
    └── Sparse domain (<100 pubs/yr) → High-precision retrieval, speculative priors
    │
[3] Exploration Pool
    ├── Generate 200 candidates (T=1.4, p=0.99)
    ├── Embed and compute convex hull
    └── Repeat with T decay until hull volume stable
    │
[4] Embedding-Hull Filter
    ├── Prune to 80 most diverse hypotheses
    └── If volume < τ → Trigger Adversarial Pool before next generation round
    │
[5] Grounding Pool
    ├── Tri-layer epistemic tagging (🟢🟡🔴)
    ├── NLI ensemble verification with cryptographic hashing
    └── Conditional: 🔴 without falsification protocol → Regenerate
    │
[6] Graveyard Agent
    ├── Search negative-results corpus
    └── Append "What Has Already Failed" to each hypothesis
    │
[7] Adversarial Pool
    ├── Inject 10 contrarian wildcards
    └── Force debate on fringe hypotheses
    │
[8] Feasibility Pool
    ├── Cross-reference lab inventory
    ├── Query vendor APIs for pricing and availability
    └── Generate structured FeasibilityReport per hypothesis
    │
[9] Meta-Reasoning Pool
    ├── Score each hypothesis on 7-axis MCDA rubric
    ├── Compute final score s = w · scores
    ├── Run pairwise ELO debates
    └── Generate counterfactual explanations
    │
[10] Human-in-the-Loop Review
     ├── Present top-N hypotheses with full provenance
     ├── Allow weight adjustment and re-ranking
     └── Confirm or modify final selection
    │
[11] Output
     ├── Top-N hypotheses with provenance
     ├── Audit trail (PDF/HTML)
     ├── Counterfactual comparisons
     └── Token-attribution heatmaps
```

Every intermediate artifact is logged to DuckDB. Nothing is hidden.

---

## 11. Deployment Modes

### 11.1 Single-User Desktop

**Target user:** Individual researcher running on a workstation.

**Stack:**
- Local LLMs via Ollama or llama.cpp (quantized, 8–70B parameters)
- Qdrant in Docker (single node)
- SQLite for state persistence
- DuckDB for audit logging
- Gradio dashboard (localhost)

**Requirements:** 32 GB RAM, NVIDIA GPU with 24 GB VRAM (or CPU-only with smaller models).

### 11.2 Lab Server (Multi-User)

**Target user:** Research group or department sharing infrastructure.

**Stack:**
- vLLM or TGI serving multiple quantized models (70–235B)
- Qdrant cluster (3 nodes for HA)
- PostgreSQL with replication
- Redis for caching and rate limiting
- Nginx reverse proxy with TLS
- OpenCode MCP server with mTLS

**Requirements:** 4–8× A100 or H100 GPUs, 256 GB RAM, SSD-backed storage.

### 11.3 Air-Gapped / Offline

**Target user:** Laboratories with no internet connectivity or strict data sovereignty requirements.

**Stack:**
- All models local (BYOM only; no LiteLLM remote providers configured)
- Pre-seeded Qdrant corpus (optional, can run on empty corpus for speculative-only mode)
- Local embedding models (BGE-M3 or nomic-embed-text)
- DuckDB audit logging (disk-based; no external sinks)
- Lab-private null-result ledger (local CSV/JSON files)

**Restrictions:**
- No vendor API queries (reagent pricing uses cached catalog snapshots)
- No external literature updates (manual ingestion via USB drive or LAN file share)
- No telemetry or crash reporting

### 11.4 Cloud-Hybrid

**Target user:** Organizations that want to use remote premium models for non-sensitive tasks while keeping sensitive data local.

**Stack:**
- LiteLLM router configured with a mix of local Ollama endpoints and remote API providers (OpenAI, Anthropic, Google)
- Sensitive data tagged with `privacy_level` metadata; private data routes exclusively to local models
- Qdrant deployed with encryption-at-rest and tenant isolation
- Audit logs split: operational metrics sent to cloud observability, content logs kept locally

---

## 12. Implementation Roadmap

| Phase | Title | Duration | Key Deliverable |
|---|---|---|---|
| 0 | Bootstrap and OpenCode Setup | 26–27 May | Repository, OpenCode config |
| 1 | Core Infrastructure and Repo Skeleton | 27 May | Directory tree, CI/CD, Docker |
| 2 | Model Abstraction and BYOK/BYOM Layer | 27 May | LiteLLM router, config system |
| 3 | State Management and Orchestration | 28 May | LangGraph topology, state schema |
| 4 | Knowledge Base and Retrieval Pipeline | 28–30 May | Qdrant, ingestion, citation hashing |
| 5 | OpenCode-Native Integration | 31 May – 1 Jun | Agents, commands, MCP, skills, plugin, Gradio MVP |
| 6 | Exploration and Adversarial Pools | 2–4 Jun | Generation engine, diversity filter |
| 7 | Grounding and Verification Pool | 5–7 Jun | Epistemic tagger, NLI verifier, UQ |
| 8 | Feasibility and Graveyard Pools | 8–10 Jun | Feasibility agent, negative-results agent |
| 9 | Tournament and Meta-Reasoning | 11–12 Jun | Debate simulator, MCDA rubric, ELO |
| 10 | Interpretability, Audit, and Transparency | 13–15 Jun | Provenance logging, counterfactuals |
| 11 | User Interfaces (Staged) | 16–19 Jun | CLI, Gradio Control Room, full dashboard |
| 12 | Fine-Tuning Pipeline | 20–22 Jun | LoRA adapters, model registry |
| 13 | Evaluation, Benchmarking, and Security | 23–27 Jun | Benchmark, red-teaming, CVE scan |
| 14 | Documentation, Community, and v1.0 | 28–30 Jun | MkDocs, community channels, launch |

---

## 13. What This Unlocks

1. **Global accessibility:** A laboratory in Nairobi or Bogotá can run the entire stack on a single rented A100 node with no API fees and no data leaving their jurisdiction.

2. **Institutional knowledge capture:** A pharmaceutical company can fine-tune every agent pool on its proprietary compound library, internal failed trials, and lab-specific protocols — without negotiating enterprise model contracts or exposing sensitive data to third-party APIs.

3. **Metascience as a practice:** A philosopher of science or metascience researcher can audit every weight, every activation, every rubric decision — turning the system itself into a research object for studying how AI-assisted discovery works and how it can be improved.

4. **Community-driven improvement:** The same open-source dynamics that made AlphaFold's *outputs* transformative are now applied to the *reasoning process itself*. The community can fork, improve, redistribute, and build on OpenHypothesis.

5. **Negative-result visibility:** Null results — the silent majority of scientific effort — become first-class citizens in the discovery process. The Graveyard Agent ensures that prior failures are mandatory reading before any new experiment begins.

6. **Full provenance for grant applications:** Every hypothesis comes with a cryptographic audit trail tracing its ancestry through specific papers, retrieval timestamps, NLI verification decisions, and MCDA scores. This transforms the grant review process from a black-box evaluation into an auditable chain of reasoning.

7. **Reproducible AI-assisted science:** Deterministic run mode ensures that scientific claims generated with OpenHypothesis can be reproduced by independent researchers, addressing a fundamental requirement of the scientific method that most AI-assisted discovery tools neglect.

---

## 14. Conclusion

OpenHypothesis is not merely an open-source reimplementation of closed-source scientific AI systems. The architectural commitments described in this document — full inspectability, user-tunable rubrics, cryptographic citation provenance, negative-result integration, wet-lab feasibility awareness, and deep developer ecosystem integration — represent a fundamentally different philosophy of how AI should assist scientific discovery.

The goal is not to replace human scientific judgment but to augment it with transparent, auditable, and improvable tools. By making every ranking decision a visible dot product, every citation a tamper-evident hash, and every agent pool a replaceable plugin, OpenHypothesis aims to align AI-assisted discovery with the core values of science itself: openness, reproducibility, and organized skepticism.

The framework is Apache 2.0 licensed, community governed, and designed to be run anywhere from a single laptop to a multi-GPU cluster. Contributions, critiques, and forks are not merely permitted — they are the point.
