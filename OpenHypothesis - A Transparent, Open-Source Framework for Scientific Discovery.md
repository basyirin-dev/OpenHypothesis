# OpenHypothesis: A Transparent, Open-Source Framework for Scientific Discovery

Below is a comprehensive architecture that directly addresses each of the six identified weaknesses of Co-Scientist, leveraging the unique advantages of open-source LLMs — namely **inspectability, fine-tunability, composability, and freedom from API-level opacity**.

---

## 1. Guiding Philosophy: Why Open-Source Wins Here

Google's Co-Scientist inherits three structural liabilities from being proprietary:

- **Opaque ranking** — users cannot see why hypothesis A beat hypothesis B.
- **Locked training signal** — the model cannot be fine-tuned on a lab's private negative results, internal protocols, or niche preprints.
- **Uniform priors** — every user gets the same Gemini-flavored worldview, amplifying echo-chamber risk.

Open-weight models (Llama 4 Scout/Maverick, Qwen3-235B, DeepSeek-V3, Gemma 3, OLMo 3, Mistral-Large-2) let us **inspect activations, retrain on counterfactual corpora, and expose every scoring rubric as editable code**. The proposal below is built on this asymmetry.

---

## 2. System Architecture: Five Specialized Agent Pools

Instead of mirroring Co-Scientist's six agents, we reorganize into **five pools** that map cleanly onto the six problems:

| Pool | Primary Role | Open-Source Stack |
|---|---|---|
| **Exploration Pool** | Divergent idea generation with enforced diversity | Qwen3-235B-A22B + vLLM, DSPy orchestrator |
| **Adversarial Pool** | Deliberate paradigm-challenge and Devil's Advocacy | Llama-4-Maverick fine-tuned on retraction/corpus-shift data |
| **Grounding Pool** | Citation verification, hallucination detection, epistemic tagging | Gemma-3-27B + custom retrieval over CrossRef/Semantic Scholar/Unpaywall |
| **Feasibility Pool** | Wet-lab reality check (cost, reagents, ethics, timeline) | DeepSeek-V3 fine-tuned on protocols.io + Bio-Protocol + OpenAlex |
| **Meta-Reasoning Pool** | Transparent ranking with user-tunable rubrics | Mistral-Large-2 + TransformerLens interpretability hooks |

All pools are orchestrated by **LangGraph** (open-source, stateful, inspectable) rather than a black-box supervisor.

---

## 3. Problem-by-Problem Mitigation

### 3.1 Echo Chambers in the "Idea Tournament"

**Root cause:** Consensus dynamics among agents trained on the same mainstream distribution.

**Mitigation — *Forced Orthogonality via Adversarial Seeding*:**

1. **Contrarian fine-tune.** Take Llama-4-Maverick and fine-tune (via Unsloth + LoRA) on a curated corpus of:
   - Retracted papers and the corrections that followed.
   - Historical paradigm shifts (Kuhn-case-study dataset: plate tectonics, H. pylori, prions, CRISPR-before-CRISPR).
   - Papers from the *Journal of Controversial Ideas*, *Research Directions*, and "negative-result" venues.
   This produces an agent whose priors are *deliberately* orthogonal to the mainstream.

2. **Embedding-space coverage constraint.** Every proposed hypothesis is embedded (using `nomic-embed-text-v1.5` or `BGE-M3`). After each tournament round, we compute the **convex hull volume** of the surviving hypotheses in embedding space. If volume shrinks below a threshold τ, the Adversarial Pool is re-invoked with an explicit prompt: *"Generate hypotheses that lie OUTSIDE this hull."* This is an algorithmic guarantee against collapse.

3. **Temperature-annealed tournament.** Early rounds run at T=1.4 with nucleus sampling p=0.99 to maximize exploration. Later rounds anneal to T=0.3. Co-Scientist's fixed-temperature debates lose this exploratory breadth.

4. **"Red Team" agent with access to pre-print fringe.** A dedicated agent ingests arXiv/bioRxiv/medRxiv daily via their open APIs, specifically weighting papers with <5 citations and from underrepresented institutions. It injects one "wildcard" hypothesis per round that the main agents are *forced* to debate rather than dismiss.

### 3.2 Verification Limited to Existing Citations

**Root cause:** "Verification" collapses into "has someone already published this?" — punishing true novelty.

**Mitigation — *Tri-Layer Epistemic Tagging*:**

Every claim in every hypothesis is tagged with one of three epistemic statuses, surfaced to the user as colored annotations:

| Tag | Definition | Verification Method |
|---|---|---|
| 🟢 **Grounded** | Directly supported by ≥2 peer-reviewed sources | Semantic Scholar + CrossRef DOI resolution + full-text PDF parsing (via `marker` + `pdftext`) |
| 🟡 **Extrapolated** | Logically consistent with grounded claims but not directly stated | Chain-of-thought audit by Gemma-3-27B; uncertainty quantified via **token-level entropy** across 32 sampling passes |
| 🔴 **Speculative** | Novel claim with no direct support | Explicitly flagged; *required* to be accompanied by a falsification protocol |

**The critical innovation:** speculative claims are **not penalized** in ranking. Instead, they are *rewarded* if paired with a well-formed falsification experiment. This flips Co-Scientist's bias: novelty is decoupled from citation count.

**Uncertainty quantification** uses the open-source `lm-polygraph` library to compute Semantic Entropy and Eigenvector Centrality over generated claim graphs — metrics unavailable from Gemini's API.

### 3.3 Hallucination in Sparse Domains

**Root cause:** When literature is thin, LLMs fill gaps with plausible-sounding fabrications.

**Mitigation — *Hard-Grounded Retrieval with Cryptographic Citation Provenance*:**

1. **Two-stage retrieval with DOI-locking.**
   - Stage 1: Hybrid BM25 + dense retrieval (Qdrant self-hosted) over a local mirror of PubMed Central, arXiv, and Unpaywall OA corpus.
   - Stage 2: Every cited claim is **cryptographically hashed** — `SHA256(DOI + paragraph_text + retrieval_timestamp)` — and the hash is stored alongside the hypothesis. This makes it impossible for a later reasoning step to "drift" the citation.

2. **Citation verifier agent.** A small, fast model (Phi-4 or Qwen3-4B) is fine-tuned *exclusively* on the task: "Given a claim and a retrieved paragraph, does the paragraph support the claim? Output {SUPPORTS, REFUTES, NEUTRAL, NOT_FOUND}." This is a **natural-language inference (NLI)** classifier, not a generative model — dramatically reducing hallucination.

3. **Ensemble disagreement as hallucination signal.** Run the grounding step on three different open-weight models (e.g., Gemma-3, Llama-4-Scout, Qwen3-30B-A3B). If they disagree on whether a citation supports a claim, the claim is auto-flagged as "disputed" and sent to human review.

4. **Domain-density detection.** Before generation, the system queries OpenAlex to estimate the **publication density** of the target subfield. Below a threshold, it automatically switches to a **high-precision / low-recall** retrieval mode and prepends a system prompt: *"You are operating in a sparsely-documented domain. Default to 🟡 Extrapolated or 🔴 Speculative tags. Do NOT fabricate citations."*

### 3.4 Lack of Wet-Lab Feasibility Assessment

**Root cause:** Theoretical elegance ≠ experimental viability.

**Mitigation — *Protocol-Aware Feasibility Agent with Live Inventory Hooks*:**

1. **Fine-tuning corpus.** Fine-tune DeepSeek-V3 on:
   - **protocols.io** (~50k open protocols with step-by-step reagent lists).
   - **Bio-Protocol** (~6k peer-reviewed methods).
   - **Addgene** plasmid availability + pricing.
   - **Sigma-Aldrich / Fisher Scientific** open catalog APIs (reagent cost & lead time).
   - **IACUC / IRB** public protocol templates (for ethical clearance awareness).

2. **Structured feasibility output.** For each top-ranked hypothesis, the Feasibility Pool returns a JSON object:
   ```json
   {
     "reagents": [{"name": "...", "vendor": "...", "cost_USD": 420, "lead_time_days": 14, "in_stock": true}],
     "equipment": ["confocal microscope", "FACS"],
     "estimated_total_cost_USD": 18500,
     "timeline_weeks": 12,
     "biosafety_level": 2,
     "ethical_clearance_needed": ["IACUC", "IRB"],
     "known_failure_modes": ["antibody X has 40% cross-reactivity per Abcam datasheet"],
     "skill_level_required": "postdoc"
   }
   ```

3. **Lab-profile integration.** Each user uploads their lab's **inventory CSV** and **equipment list** once. The agent cross-references and flags mismatches ("Your lab lacks a cryo-EM; this hypothesis requires one — collaboration needed").

4. **Cost-aware ranking.** Feasibility score becomes a first-class dimension in the tournament, weighted by the user (see §3.5).

### 3.5 Black-Box Ranking Criteria

**Root cause:** Users cannot interrogate *why* one hypothesis won.

**Mitigation — *Interpretable, User-Tunable Multi-Criteria Decision Analysis (MCDA)*:**

1. **Explicit rubric, not latent scoring.** Replace the opaque pairwise-debate ranking with a transparent rubric. Each hypothesis is scored on **7 axes**, each 0–10:
   - Novelty (embedding-distance from known literature)
   - Groundedness (% of 🟢 claims)
   - Falsifiability (quality of proposed falsification experiment, scored by NLI agent)
   - Feasibility (from §3.4)
   - Impact potential (citation-velocity of the subfield)
   - Diversity-contribution (marginal gain to embedding-hull volume)
   - Risk-reward (speculative-claim ratio × falsification quality)

2. **User-adjustable weights.** A slider UI (built in Gradio or Streamlit) lets each researcher set their own weight vector **w**. A wet-lab PI can boost Feasibility; a theorist can boost Novelty. The final score is simply **s = w · scores** — fully auditable.

3. **Attribution via interpretability tooling.** Using **TransformerLens** or **SAE (Sparse Autoencoder)** features from the open-source `sae-lens` library, we can extract which input tokens most influenced the Ranking agent's score for each axis. These are rendered as heatmaps next to each hypothesis.

4. **Counterfactual explanations.** For any pair (A, B) where A ranked higher, the system auto-generates: *"A beat B because [Feasibility: +3.2, Novelty: −1.1, ...]. If you had weighted Feasibility at ≤0.15 instead of 0.30, B would have won."* This is impossible with a proprietary API.

### 3.6 No Integration of Negative / Null Results

**Root cause:** Training data and retrieval skew toward positive findings.

**Mitigation — *Negative-Result-First Retrieval and "Graveyard" Agent*:**

1. **Dedicated negative-results corpus.** Index:
   - *Journal of Negative Results in BioMedicine* (archived), *PLOS ONE* null-result papers, *F1000Research* registered reports with null outcomes.
   - **Open Science Framework (OSF)** registered reports.
   - **ClinicalTrials.gov** — specifically trials with `study_results = "no"` or `status = "terminated"`.
   - **PubChem BioAssay** inactive-compound records (~100M negative data points).
   - **ChEMBL** inactive assays.

2. **"Graveyard" agent.** Before any hypothesis is finalized, this agent queries the negative-results corpus for:
   - Prior failed attempts on the same target/mechanism.
   - Structurally similar hypotheses that were tested and falsified.
   - Known off-target effects or confounds.
   
   Output is appended to every hypothesis as a **"What Has Already Failed"** section — transforming null results from invisible into mandatory context.

3. **Negative-result reward signal.** During tournament ranking, hypotheses that *explicitly cite and learn from* prior negative results receive a bonus on the Groundedness axis. This inverts the usual incentive.

4. **Lab-private null-result ledger.** Each lab can upload its own failed experiments (stored locally, never sent to any API — a privacy advantage of open-source). The Grounding Pool treats these as first-class citations, preventing a lab from re-testing a hypothesis it already falsified in-house two years ago.

---

## 4. Integrated Workflow

```
User defines research question
         │
         ▼
[Domain-Density Check] ──► sets retrieval mode & epistemic priors
         │
         ▼
[Exploration Pool] ──► 200 candidate hypotheses (T=1.4)
         │
         ▼
[Embedding-Hull Filter] ──► prunes to diverse 80
         │
         ▼
[Grounding Pool] ──► tri-layer tags + cryptographic citations
         │
         ▼
[Graveyard Agent] ──► appends prior failures
         │
         ▼
[Adversarial Pool] ──► injects 10 contrarian wildcards
         │
         ▼
[Feasibility Pool] ──► structured JSON per hypothesis
         │
         ▼
[Meta-Reasoning Pool] ──► 7-axis rubric × user weights
         │
         ▼
Top-10 hypotheses with full provenance, heatmaps, counterfactuals
```

Every intermediate artifact is logged to a local **SQLite + DuckDB** store, queryable by the researcher. Nothing is hidden.

---

## 5. Implementation Roadmap (12 weeks, ~3 engineers)

| Phase | Weeks | Deliverable |
|---|---|---|
| **0. Infra** | 1–2 | vLLM cluster (4×A100 or 8×L40S), Qdrant, LangGraph orchestrator, SQLite store |
| **1. Fine-tuning** | 3–5 | LoRA adapters for Adversarial (Llama-4), Feasibility (DeepSeek-V3), NLI-verifier (Phi-4) via Unsloth |
| **2. Retrieval** | 4–6 | OpenAlex + PMC + negative-results ingestion; DOI-locking + hashing |
| **3. Rubric & UI** | 6–8 | 7-axis scoring, Gradio dashboard with weight sliders, heatmaps |
| **4. Integration** | 8–10 | End-to-end pipeline, lab-profile upload, private null-result ledger |
| **5. Eval** | 10–12 | Benchmark against Co-Scientist's published results (antimicrobial resistance, plant immunity, liver fibrosis cases); release open benchmark dataset |

Estimated compute cost: **~$15k** for fine-tuning + **~$8k/month** inference at modest scale — orders of magnitude cheaper than Gemini API at equivalent throughput, and with no per-token lock-in.

---

## 6. What This Unlocks That Co-Scientist Cannot

1. **A lab in Nairobi or Bogotá** can run the entire stack on a single rented A100 node, with no API fees and no data leaving their jurisdiction.
2. **A pharma company** can fine-tune the Feasibility agent on its proprietary compound library without negotiating an enterprise Gemini contract.
3. **A philosopher of science** can audit every weight, every activation, every rubric decision — turning the system itself into a research object.
4. **The community** can fork, improve, and redistribute — the same dynamic that made AlphaFold's *outputs* transformative, now applied to the *reasoning process itself*.

---

### Bottom Line

The "absolute best" mitigation is not a patch on Co-Scientist — it is an **open-weight, inspectable, user-tunable, negative-result-aware, cryptographically grounded, feasibility-aware multi-agent framework** where every ranking decision is a dot product the user can see and change. Open-source LLMs are not a cheaper substitute here; they are the *only* substrate on which these six problems can be structurally, rather than cosmetically, solved.