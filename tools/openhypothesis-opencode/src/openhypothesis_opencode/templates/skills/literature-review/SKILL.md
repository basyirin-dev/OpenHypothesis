---
name: literature-review
description: >-
  Use when verifying citations against the Qdrant corpus, applying epistemic
  tags (grounded/extrapolated/speculative/contradicted) to scientific claims,
  mining negative-results databases, and generating provenance audit trails.
---

# Literature Review

Methodology for citation verification, epistemic tagging, and negative-results mining within OpenHypothesis.

## Epistemic Tagging Protocol

Every claim must be assigned one of four epistemic tags, defined in `src/openhypothesis/state/schema.py`:

| Tag | Criteria | Action |
|---|---|---|
| 🟢 **Grounded** | ≥2 peer-reviewed sources with cosine similarity > 0.9 AND NLI label = "entailment" | Proceed |
| 🟡 **Extrapolated** | ≥1 source with score > 0.7, claim is logically consistent but not directly stated | Proceed with caution |
| 🔴 **Speculative** | No sources above 0.7 threshold | Require falsification protocol |
| ⛔ **Contradicted** | NLI label = "contradiction" from ≥1 source with score > 0.9 | Route to graveyard or flag for human review |

The `ground_node` in `src/openhypothesis/agents/nodes.py` applies these tags after searching Qdrant.

## Citation Hash Verification

Every citation must carry a cryptographic hash computed as:

```
SHA256(normalized_doi | "|" | chunk_text | "|" | retrieval_timestamp_iso)
```

Implementation in `src/openhypothesis/tools/citation_hasher.py`:

```python
from openhypothesis.tools.citation_hasher import CitationHasher

h = CitationHasher.hash(doi="10.1234/example", chunk_text="Gene X regulates Y.")
assert CitationHasher.verify(doi="...", chunk_text="...", timestamp=..., hash_value=h)
```

**Rules:**
- A claim is only citable if it traces back to a valid hash in the Qdrant payload.
- If the hash does not match (citation drift), flag for human review. Do not accept the citation as-is.
- Hash mismatch is a stronger signal than low similarity — it means the text has been modified from the original.

## NLI Verification Workflow

1. Retrieve top-k chunks from Qdrant for the claim.
2. Pass each (claim, chunk) pair through an NLI model (e.g., DeBERTa-v3-large fine-tuned on SciFact).
3. Classify as **entailment** (supports), **contradiction** (refutes), or **neutral** (not enough info).
4. Ensemble check: run verification across two distinct models. If their classifications diverge, flag the claim for human review.
5. Store the NLI label in the `Citation.nli_label` field.

If no NLI model is available locally, fall back to: score > 0.9 → treat as entailment; score < 0.5 → treat as neutral.

## Negative-Results Mining

Before finalizing any hypothesis, search for prior failed attempts on the same target or mechanism.

**Databases to query:**
- **ClinicalTrials.gov** — terminated/completed trials with null outcomes
- **PubChem BioAssay** — inactive assay results (active = 0)
- **OSF Registered Reports** — null results with DOI
- **ChEMBL** — inactive compounds with assay details

**Workflow:**
1. Embed the target/mechanism using `create_embedder`.
2. Search the `negative_results` Qdrant collection (ingested from the databases above).
3. Search the conversation history for previously discarded graveyard hypotheses.
4. If matches found, include a "What Has Already Failed" section in the output.

## "What Has Already Failed" Appendix

Template format appended to every hypothesis before finalization:

```markdown
### What Has Already Failed

| Target | Mechanism | Failure Reason | Source |
|---|---|---|---|
| KRAS G12C | Covalent inhibition | Toxicity at therapeutic doses | PMID: 34567890 |
| [target] | [mechanism] | [failure reason] | [DOI/PMID] |
```

If no prior failures are found, state: *"No prior failed attempts found for this target in the indexed negative-results corpus."*

## Provenance Audit

Every claim and hypothesis should be traceable through the LangGraph pipeline:

- **Which node generated it?** (`generated_by` field on `Hypothesis`)
- **What model was used?** (tracked via `ModelRouter` cost records)
- **What citations support it?** (`supporting_citations` with NLI labels and hashes)
- **What was its epistemic trajectory?** (initial tag → after grounding → after debate)
- **Who (which agent) last modified it?** (debate transcripts, regeneration cycles)

Use the checkpointer (`create_checkpointer` in `src/openhypothesis/state/checkpoint.py`) to load full state by `thread_id` and walk the audit trail.

## Integration Points

- **Epistemic tags:** `EpistemicTag` enum in `src/openhypothesis/state/schema.py`
- **Citation hashing:** `CitationHasher` in `src/openhypothesis/tools/citation_hasher.py`
- **Vector search:** `VectorStore` in `src/openhypothesis/tools/retriever.py`
- **Embedding:** `create_embedder` in `src/openhypothesis/tools/embedder.py`
- **Checkpointer:** `create_checkpointer` in `src/openhypothesis/state/checkpoint.py`
- **NLI:** DeBERTa-v3-large on SciFact (or `lm-polygraph` for ensemble)
- **Negative-results ingestion:** `tools/ingest.py` pulls from ClinicalTrials.gov, PubChem, OSF, ChEMBL
