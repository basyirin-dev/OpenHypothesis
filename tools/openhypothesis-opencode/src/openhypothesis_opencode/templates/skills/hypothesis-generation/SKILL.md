---
name: hypothesis-generation
description: >-
  Use when generating diverse, novel scientific hypotheses with controlled
  temperature annealing (T=1.4 exploration to T=0.3 convergence). Covers
  embedding-hull diversity enforcement, structured output schemas, and
  falsification protocol requirements.
---

# Hypothesis Generation

Methodology for divergent scientific hypothesis generation within the OpenHypothesis exploration pipeline.

## Temperature Annealing Schedule

The exploration pool uses a decaying temperature schedule to balance exploration vs. convergence:

| Round | Temperature | Behavior |
|---|---|---|
| 1–2 | T=1.4 | Maximum divergence. Generate broad, unconventional, cross-domain hypotheses. |
| 3–4 | T=1.0 | Moderate exploration. Begin filtering against the research question constraints. |
| 5–6 | T=0.7 | Convergence. Favor mechanistically plausible hypotheses. |
| 7+ | T=0.3 | Strict convergence. Only refine and rank existing candidates. |

When instructing an LLM for hypothesis generation, specify the target temperature in the system prompt. The `ModelRouter` in `src/openhypothesis/tools/model_router.py` passes this to the provider.

## Structured Output Schema

Every hypothesis must conform to the `Hypothesis` Pydantic model from `src/openhypothesis/state/schema.py`:

```json
{
  "statement": "string — the core hypothesis",
  "rationale": "string — why this is worth investigating",
  "mechanism": "string — proposed molecular/causal mechanism",
  "expected_outcome": "string — predicted experimental result",
  "confidence": 0.0..1.0,
  "falsification_protocol": {
    "experiment_design": "string",
    "predicted_outcome": "string",
    "key_assumptions": ["string"],
    "controls": ["string"]
  }
}
```

Never emit raw strings — always validate against this structure before returning.

## Diversity Enforcement

The embedding-hull filter (`agents/exploration/`) tracks the convex hull volume of surviving hypotheses in embedding space:

- If hull volume contracts below threshold **τ**, the adversarial pool is triggered to generate out-of-hull hypotheses.
- Track diversity via `scipy.spatial.ConvexHull` over the embedding vectors.
- If the pool is stuck generating variations on a single theme, explicitly prompt: *"Generate a hypothesis outside the current embedding hull. The existing cluster centres on [summary]. Propose something mechanistically orthogonal."*

## Falsification Protocol Rule

Every **🔴 Speculative** claim **must** carry a `falsification_protocol` JSON object. If the LLM omits it:

1. The `regenerate` node adds one automatically (stub).
2. After `MAX_REGENERATION_CYCLES` (defined in `src/openhypothesis/agents/graph_builder.py`), hypotheses still lacking a protocol are sent to the graveyard.
3. Graveyard entries are discarded — they do not proceed to debate or ranking.

## Integration Points

- **Model config:** `config.yaml` → `models.exploration` profile
- **LLM routing:** `ModelRouter` in `src/openhypothesis/tools/model_router.py`
- **State schema:** `Hypothesis`, `FalsificationProtocol` in `src/openhypothesis/state/schema.py`
- **Pipeline topology:** `src/openhypothesis/agents/graph_builder.py` defines the exploration → filter → ground → graveyard flow
- **Embedding:** `create_embedder` in `src/openhypothesis/tools/embedder.py`
