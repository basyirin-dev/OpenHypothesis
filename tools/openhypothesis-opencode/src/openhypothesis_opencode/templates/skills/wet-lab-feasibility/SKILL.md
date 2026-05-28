---
name: wet-lab-feasibility
description: >-
  Use when assessing the practical feasibility of running an experiment —
  reagent pricing, biosafety levels, equipment matching against lab inventory,
  protocol costing, and timeline estimation.
---

# Wet-Lab Feasibility

Methodology for assessing the practical feasibility of experimental protocols within OpenHypothesis.

## Reagent Estimation

Estimate required reagents by breaking the protocol into steps and assigning typical reagents per category:

| Category | Typical Reagents | Price Range |
|---|---|---|
| Molecular cloning | Enzymes (restriction, ligase, polymerase), primers, plasmids, gels | $50–$500 |
| Cell culture | Media, sera, antibiotics, transfection reagents, growth factors | $100–$2,000 |
| Protein work | Antibodies (primary/secondary), beads, columns, buffers | $200–$5,000 |
| Genomics | Sequencing libraries, adapters, flow cells, qPCR probes | $500–$10,000 |
| Animal models | Mice (WT/KO), compounds for dosing, surgical supplies | $1,000–$20,000 |
| Specialized | CRISPR guides, AAV vectors, lentivirus, organoid kits | $500–$5,000 |

**Pricing sources:** Addgene (plasmid catalog), Sigma-Aldrich (reagent catalog), protocols.io (published protocols).

## Biosafety Level Assessment

Determine BSL using this decision tree:

1. Is the organism/agent risk group 1 (non-pathogenic)? → **BSL-1**
2. Risk group 2 (moderate hazard, treatable)? → **BSL-2**
3. Risk group 3 (serious, potentially lethal, treatable)? → **BSL-3**
4. Risk group 4 (high risk, untreatable)? → **BSL-4**

For recombinant DNA: refer to NIH Guidelines. Any work with human-derived materials (cell lines, tissue) typically requires BSL-2 with additional precautions. If the user's lab inventory does not list a BSL certification matching the required level, flag this as a blocker.

## Equipment Matching

Cross-reference required equipment against the user's lab inventory CSV:

| Equipment | Typical Experiments | Alternative / Core Facility |
|---|---|---|
| Thermocycler | Cloning, genotyping, qPCR | Core facility available at ~$5/run |
| Centrifuge (refrigerated) | Cell pelleting, protein prep | Shared lab equipment |
| FACS / Flow cytometer | Cell sorting, immunophenotyping | Core facility $50–$200/hr |
| HPLC / FPLC | Protein purification | Core facility or shared |
| Microscope (confocal) | Imaging, IF | Core facility $50–$150/hr |
| Incubator (CO₂) | Cell culture | Shared lab equipment |

If the required equipment is missing and no core facility alternative is listed, flag the feasibility score down.

## Cost Estimation Methodology

Total cost = **Reagents** + **Consumables** + **Personnel** + **Equipment time** + **Overhead**

| Component | Estimation Method |
|---|---|
| Reagents | Vendor catalog prices + shipping (15%) |
| Consumables | Pipette tips, tubes, plates: ~$50–$200 per experiment |
| Personnel | Hours × (technician $25/hr, postdoc $40/hr, PI $80/hr) |
| Equipment time | Core facility rates or $10–$50/hr for shared lab gear |
| Overhead | 30–50% institutional overhead on direct costs |

## Timeline Projection

Provide optimistic/pessimistic bounds per phase. Example for a CRISPR knockout + validation experiment:

| Phase | Optimistic | Pessimistic |
|---|---|---|
| Guide design & cloning | 1 week | 2 weeks |
| Transfection & selection | 2 weeks | 4 weeks |
| Knockout validation (PCR + WB) | 1 week | 3 weeks |
| Phenotypic assay | 2 weeks | 6 weeks |
| **Total** | **6 weeks** | **15 weeks** |

## Failure Mode Catalog

Common failure modes to check for each technique:

- **CRISPR:** Off-target effects, inefficient cutting, polyclonal variation
- **RNAi:** Off-target silencing, transfection toxicity, partial knockdown
- **Protein expression:** Insoluble protein, low yield, degradation
- **Animal models:** Non-penetrance, background effects, sample size underpowered
- **Clinical relevance:** Dose translation failure, species-specific biology

## Go/No-Go Thresholds

| Condition | Recommendation |
|---|---|
| Total cost > $100k | Recommend partnership or grant application |
| Missing BSL-3/4 capability | Defer until facility access secured |
| Timeline > 52 weeks | Flag for scope reduction or phased approach |
| Unavailable key reagent | Check alternative suppliers or synthesis services |

## Integration Points

- **Feasibility schema:** `FeasibilityReport`, `ReagentItem` in `src/openhypothesis/state/schema.py`
- **Lab profile:** user-uploaded CSV with columns: `equipment, bsl_level, core_facilities, inventory`
- **Pipeline:** the `feasibility` node in `src/openhypothesis/agents/nodes.py` (stub → replace with these guidelines)
