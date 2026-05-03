# Stage 2 DSL Ontology Builder Skill Improvement Design

Date: 2026-05-03
Skill: stage2-dsl-ontology-builder
Status: design approved

## Problem Statement

The current `stage2-dsl-ontology-builder` skill has three critical weaknesses:

1. **Input parsing is text-based, not structured.** `bootstrap_stage2.py` concatenates all Stage 1 YAML files into a single string and does keyword matching. It loses the structured relationships between cards, constraints, risks, evidence, and knobs that Stage 1 already produces.
2. **Templates are hard-coded, not evidence-driven.** Modules, fields, validators, and lowering passes are defined as Python dictionaries in the script. They cannot adapt to new optimization patterns discovered by Stage 1.
3. **Quality gate is structural, not semantic.** `check_stage2_quality.py` checks only file existence and keyword presence. It cannot verify that a schema field is backed by evidence, that a high-risk card has a validator, or that shadow DSL actually covers Stage 1 fields.

The result: the skill produces a scaffold that requires heavy manual refinement. The evidence chain from source code -> Stage 1 -> Stage 2 is broken at the parsing layer.

## Design Goals

- Parse Stage 1 structured YAML into a typed internal representation (EvidenceGraph).
- Generate Stage 2 artifacts by traversing EvidenceGraph, not by emitting hard-coded templates.
- Validate Stage 2 output semantically against EvidenceGraph, not structurally against file lists.
- Support incremental regeneration when Stage 1 evidence changes.
- Keep backward compatibility with existing `bootstrap_stage2.py` and `check_stage2_quality.py` entrypoints.

## Architecture

### Three-Layer Pipeline

```text
Stage 1 YAML outputs
      │
      ▼
┌────────────────────────────────────┐
│  Layer 1: EvidenceGraph Builder    │  (stage2_parser.py)
│  - Parse structured YAML           │
│  - Build typed node graph          │
│  - Resolve cross-references        │
└────────────────────────────────────┘
      │  .evidence_graph.json
      ▼
┌────────────────────────────────────┐
│  Layer 2: Synthesizer              │  (stage2_synthesizer.py)
│  - Infer modules from field paths  │
│  - Generate schemas from cards     │
│  - Derive validators from risks    │
│  - Emit shadow DSL from evidence   │
└────────────────────────────────────┘
      │  stage2_outputs/
      ▼
┌────────────────────────────────────┐
│  Layer 3: Semantic Verifier        │  (stage2_verifier.py)
│  - Evidence connectivity check     │
│  - Field completeness check        │
│  - Knob-to-field mapping check     │
│  - Validator coverage check        │
│  - Shadow DSL coverage check       │
└────────────────────────────────────┘
      │  review/quality_gate.json
      ▼
   pass / warn / fail
```

Each layer is an independent script that can run alone. This enables debugging and incremental work.

## Layer 1: EvidenceGraph Builder

### Input

Reads the following Stage 1 artifact files:

- `cards/optimization_cards.yaml`
- `knobs/tunable_knobs.yaml`
- `constraints/constraints.yaml`
- `constraints/forbidden_transforms.yaml`
- `risks/risks.yaml`
- `evidence/source_evidence.yaml`
- `auxiliary/pipeline_graphs.yaml`
- `auxiliary/workspace_layout.yaml`
- `dsl/suggested_dsl_sections.yaml`
- `annotations/files/*.yaml` (for function-level evidence)

### Node Types

| Node type | Source YAML | Key fields |
|---|---|---|
| `card` | `optimization_cards.yaml` | id, canonical_name, possible_dsl_fields, source_evidence, constraints, risks |
| `constraint` | `constraints.yaml` | id, description, source_evidence_ids, related_forbidden_transform_ids |
| `risk` | `risks.yaml` | id, description, related_forbidden_transform_ids |
| `forbidden_transform` | `forbidden_transforms.yaml` | id, scope, forbidden_change, source_evidence_ids |
| `evidence` | `source_evidence.yaml` | id, file, symbol, line_range, observed_fact, confidence |
| `knob` | `tunable_knobs.yaml` | name, type, domain, searchable, coupled_constraints |
| `dsl_field` | Inferred from card.possible_dsl_fields | path, meaning, confidence |
| `pipeline_node` | `pipeline_graphs.yaml` | id, canonical_name, owner, alias_of |
| `workspace_region` | `workspace_layout.yaml` | region_id, size_formula, producer_functions, consumer_functions |
| `suggested_section` | `suggested_dsl_sections.yaml` | name, purpose, fields |

### Edge Types

| From | To | Label | Derivation |
|---|---|---|---|
| `card` | `dsl_field` | `suggests` | card.possible_dsl_fields[] |
| `card` | `evidence` | `backed_by` | card.source_evidence[].id |
| `card` | `constraint` | `constrained_by` | card.constraints[] |
| `card` | `risk` | `risked_by` | card.risks[] |
| `constraint` | `forbidden_transform` | `forbids` | constraint.related_forbidden_transform_ids[] |
| `risk` | `forbidden_transform` | `forbids` | risk.related_forbidden_transform_ids[] |
| `forbidden_transform` | `evidence` | `backed_by` | ft.source_evidence_ids[] |
| `constraint` | `evidence` | `backed_by` | constraint.source_evidence_ids[] |
| `knob` | `constraint` | `couples_to` | knob.coupled_constraints[] |
| `pipeline_node` | `evidence` | `backed_by` | node.source_evidence_ids[] |
| `workspace_region` | `evidence` | `backed_by` | region.source_evidence_ids[] |
| `dsl_field` | `knob` | `tuned_by` | Exact match: knob.name == dsl_field.path last segment, or knob.name appears as a whole word in dsl_field.meaning |

### Intermediate Output

`.evidence_graph.json` — a JSON-serialized graph with nodes and edges. This file is the single source of truth for Layers 2 and 3.

### Capabilities

- **Connectivity analysis**: Does every card have at least one evidence node reachable via `backed_by`?
- **Coverage analysis**: Which dsl_field nodes have multiple card sources (high confidence) vs. single source (weak)?
- **Risk aggregation**: Which forbidden_transform nodes are referenced by multiple risks/constraints (high-priority validators)?

## Layer 2: Synthesizer

### Module Inference

Map `dsl_field.path` first token to ontology module using a configurable rule file `scripts/module_inference_rules.yaml`:

```yaml
rules:
  - token: memory
    module: memory
  - token: pipeline
    module: pipeline
  - token: mla
    module: compute
  - token: flash_decode
    module: decode
  - token: workspace
    module: workspace
  - token: shape_layout
    module: shape
  - token: tiling
    module: tiling
  # ... etc

fallback: needs_review
```

Rules are ordered; first match wins. Unknown tokens fall back to `needs_review` and are flagged in `review/missing_fields.md`.

### Schema Field Generation

For each `dsl_field` node, generate a schema entry with attributes derived from evidence:

| Attribute | Derivation rule |
|---|---|
| `type` | From `dsl_field.meaning`: "coordinate/key/signature" -> `string`; "formula/sequence" -> `object`; "size/count" -> `int`; "enabled/flag" -> `bool` |
| `searchable` | `true` if the field path matches a knob name or appears in a knob's `consumers` list |
| `editable_policy` | `searchable` if searchable; `configurable` if meaning involves "policy/order/mode"; `fixed` if meaning involves "formula/identity"; `forbidden` if path is in a forbidden_transform scope |
| `source_cards` | All cards that have this field in `possible_dsl_fields` |
| `source_evidence` | Union of all evidence nodes reachable from those cards |
| `related_validators` | Derived from risks/constraints linked to those cards (see Validator Generation) |
| `lowering_consumers` | Inferred from field path: `memory.l1.*` -> LowerL1Residency; `workspace.*` -> LowerWorkspaceLayout; etc |

### Validator Generation

For each `risk` node with severity >= high, derive a validator spec:

1. Find all `forbidden_transform` nodes reachable from the risk via `forbids` edges.
2. Find all `constraint` nodes that also point to those forbidden transforms.
3. Find all `evidence` nodes backing those constraints/transforms.
4. Generate validator: `name` = `risk.id` lowercased with `valid_` prefix; `expr` = heuristic template derived from constraint description keywords (e.g., "must wait X" -> `pipeline.stage_graph.edges[].contains(X)`). In v1 this is rule-based, not NLP.

Example:
- Risk `R-GQA-V-L1-LIFETIME` -> FT `FT-NO-ELIDE-GQA-V-L1-RELEASE` -> Constraint `C-GQA-MM2-SYNC`
- Validator: `l1_residency_loop_order`, expr derived from "must wait syncV1C2, preserve V reuse/release guard"

Mandatory validators (hard-coded list that must exist regardless of evidence):
- `ub_capacity`
- `l1_capacity`
- `workspace_no_alias`
- `sparse_window_alignment`
- `split_kv_lse_merge_valid`
- `event_dependency_valid`
- `l1_residency_loop_order`

If EvidenceGraph does not yield evidence for a mandatory validator, it is still emitted with `needs_evidence: true` and flagged by the verifier.

### Lowering Pass Generation

For each lowering pass in the mandatory list:

- `consumes`: derived from which modules have fields touching that pass's domain
- `emits`: derived from `dsl_field.meaning` (what code artifact the field lowers to)
- `patch_points`: derived from `pipeline_graphs` node canonical_names and `workspace_layout` producer/consumer functions
- `pre_validators`: union of validators for all consumed modules

### Shadow DSL Generation

Shadow DSL is generated per variant (nonquant, gqa, mla, flash_decode):

1. Collect all `card` nodes whose `applies_to.variants` include the target variant.
2. Collect all `dsl_field` nodes reachable from those cards with `confidence >= high`.
3. Group fields by module.
4. For each field, extract a concrete value from Stage 1 evidence when available (e.g., from `workspace_layout` size formulas, from `pipeline_graphs` node canonical_names).
5. Emit one YAML file per variant: `examples/<variant>_shadow.yaml`.

Coverage is computed as: `covered_high_confidence_fields / total_high_confidence_fields` per variant.

### Incremental Mode

When `--incremental` is passed:

1. Compute a content hash for each evidence node.
2. Compare against previous run's `.evidence_graph.json`.
3. Only regenerate files whose upstream evidence nodes have changed.
4. Files with no changed dependencies are copied from `--previous` unchanged.

This enables fast iteration when only a few Stage 1 artifacts change.

## Layer 3: Semantic Verifier

### Scoring Dimensions (100 points total)

| Dimension | Weight | What it checks |
|---|---|---|
| Evidence connectivity | 20 | Every card has an evidence path; every evidence node has file+symbol; every dsl_field has a card source |
| Field design completeness | 20 | Every schema field has type, meaning, editable_policy; no "needs evidence mapping" placeholders; searchable fields have candidates/range |
| Searchable knob quality | 15 | Every searchable field maps to a Stage 1 knob; knob domain maps to field candidates/range |
| Validator completeness | 20 | Every high-risk card has >=1 validator; mandatory validators exist; validators have non-placeholder expr |
| Lowering spec clarity | 10 | Every pass has consumes, emits, patch_points; patch_points trace to pipeline_graphs or workspace_layout |
| Shadow DSL coverage | 15 | Per-variant coverage >= 80%; all variants represented |

### Scoring Rules

- **Evidence connectivity (20)**:
  - Card without evidence path: -3/card
  - Evidence node missing file or symbol: -2/node
  - dsl_field without card source: -2/field

- **Field design completeness (20)**:
  - Missing type or meaning: -2/field
  - Searchable field without candidates/range: -3/field
  - Placeholder "needs evidence" marker: -1/instance

- **Searchable knob quality (15)**:
  - Searchable field with no corresponding knob: -3/field
  - Knob domain not mapped to field range: -2/field

- **Validator completeness (20)**:
  - High-risk card without validator: -4/card
  - Missing mandatory validator: -5/validator
  - Validator with placeholder expr: -2/validator

- **Lowering spec clarity (10)**:
  - Missing consumes/emits/patch_points: -2/item
  - Patch point not traceable to evidence: -1/point

- **Shadow DSL coverage (15)**:
  - >= 80% per variant: full points
  - 60-80%: proportional
  - < 60%: 0 points for that variant

### Hard Failures (fail regardless of score)

- Any DSL module has no source card.
- Any high-risk field has no validator.
- Any searchable field has no candidates or range.
- L1 residency fields lack `l1_capacity` validator.
- L1 residency across G lacks `l1_residency_loop_order` validator.
- split-KV lacks `workspace_no_alias` validator.
- split-KV lacks `split_kv_lse_merge_valid` validator.
- workspace fields lack `workspace_no_alias` validator.
- No variant can be represented as shadow DSL.

### Output Format

`review/quality_gate.json` — compatible with existing output contract, extended with semantic detail:

```json
{
  "overall_status": "pass|warn|fail",
  "total_score": 87,
  "scores": {
    "card_to_module_coverage": 18,
    "field_design_completeness": 18,
    "searchable_knob_quality": 13,
    "validator_completeness": 18,
    "lowering_spec_clarity": 10,
    "shadow_dsl_coverage": 10
  },
  "hard_failures": [],
  "semantic_issues": [
    {
      "severity": "error",
      "category": "evidence",
      "message": "Card OC-MLA-NUPDATE-SIDECHANNEL has no evidence path",
      "remediation": "Add source_evidence entries or mark as needs_evidence: true"
    }
  ],
  "coverage": {
    "shadow_dsl": {
      "gqa": {"covered": 8, "total": 12, "pct": 66.7},
      "mla": {"covered": 10, "total": 14, "pct": 71.4},
      "flash_decode": {"covered": 6, "total": 8, "pct": 75.0}
    }
  },
  "next_actions": [
    "Fix 1 evidence path in OC-MLA-NUPDATE-SIDECHANNEL",
    "Add l1_residency_loop_order validator for GQA fields"
  ]
}
```

### Thresholds

- `>= 85` and no hard failures: **pass** — ready to implement validators or lowering MVP.
- `70-84` and no hard failures: **warn** — must fix listed issues first.
- `< 70` or any hard failure: **fail** — do not proceed; revisit Stage 1 or redo schema design.

## Agent Workflow

### Roles

| Role | Input | Output | Tool |
|---|---|---|---|
| Parser Agent | Stage 1 output directory | `.evidence_graph.json` | `stage2_parser.py` |
| Synthesizer Agent | `.evidence_graph.json` + `module_inference_rules.yaml` | `stage2_outputs/` | `stage2_synthesizer.py` |
| Verifier Agent | `.evidence_graph.json` + `stage2_outputs/` | `review/quality_gate.json` | `stage2_verifier.py` |
| Shadow Builder Agent (conditional) | `.evidence_graph.json` + current shadow DSL | Updated shadow examples | Manual or `stage2_synthesizer.py --fix-shadow` |

### Orchestration

```text
Stage 1 outputs
    │
    ▼
Parser Agent
    │  .evidence_graph.json
    ▼
Synthesizer Agent
    │  stage2_outputs/
    ▼
Verifier Agent
    │
    ├─ score >= 85, no hard failures ──► DONE
    │
    ├─ 70 <= score < 85 ──► report issues, user fixes, re-run Verifier
    │
    └─ score < 70 or hard failures ──►
         ├─ If evidence graph is sparse: go back to Stage 1
         └─ If generation rules are wrong: adjust module_inference_rules.yaml, re-run Synthesizer
```

### Backward Compatibility

- `scripts/bootstrap_stage2.py` is preserved as a shim. It prints a deprecation warning and delegates to `stage2_parser.py` followed by `stage2_synthesizer.py`.
- `scripts/check_stage2_quality.py` is preserved as a shim. It prints a deprecation warning and delegates to `stage2_verifier.py`.
- The output directory structure (`stage2_outputs/ontology/`, `stage2_outputs/schema/`, etc.) remains unchanged.
- `review/quality_gate.json` format is a superset of the old format; existing consumers should still work.

## Files to Create/Modify

### New files

- `scripts/stage2_parser.py` — EvidenceGraph builder
- `scripts/stage2_synthesizer.py` — Artifact synthesizer
- `scripts/stage2_verifier.py` — Semantic verifier
- `scripts/module_inference_rules.yaml` — Module mapping rules
- `tests/test_parser.py` — Parser unit tests
- `tests/test_synthesizer.py` — Synthesizer unit tests
- `tests/test_verifier.py` — Verifier unit tests
- `tests/fixtures/` — Minimal Stage 1 YAML fixtures for testing

### Modified files

- `SKILL.md` — Update workflow, agent definitions, script entrypoints
- `README.md` — Update quick-start commands
- `references/stage2_workflow.md` — Update to reference new pipeline
- `references/output_contract.md` — Extend quality_gate.json contract with semantic fields
- `agents/openai.yaml` — Add agent role definitions and orchestration hints
- `scripts/bootstrap_stage2.py` — Add deprecation shim
- `scripts/check_stage2_quality.py` — Add deprecation shim

### Deleted (no longer needed)

None. Old scripts become shims.

## Test Strategy

### Unit tests

- `test_parser.py`: Load minimal fixtures, verify node/edge counts, verify connectivity for a known card-evidence pair.
- `test_synthesizer.py`: Given a small evidence graph, verify generated schema has expected fields, validators, and lowering passes.
- `test_verifier.py`: Given a known-good and known-bad stage2 output, verify scores and hard failures.

### Integration test

- Run full pipeline against actual `artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction/`.
- Verify output passes quality gate (`>= 85`).
- Verify shadow DSL coverage >= 80% for gqa, mla, flash_decode.

### Regression test

- Compare new output against old `bootstrap_stage2.py` output for structural equivalence (same files exist, same top-level keys).

## Risk and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| New parser fails on edge-case Stage 1 YAML | High | Parser has fallback to raw-text mode; shim preserves old behavior on error |
| Module inference rules miss new patterns | Medium | Rules are external YAML, easy to extend; unknown tokens are flagged, not silently dropped |
| Synthesizer generates too many `needs_evidence` fields | Medium | Verifier catches this; threshold tuned to 20 placeholders max (same as old script) |
| Semantic verifier is too strict | Low | Thresholds are the same as old (85/70); hard failures match old SKILL.md constraints |
| Incremental mode has stale-cache bugs | Low | Incremental is opt-in; default is full regeneration |

## Next Steps

After this design is approved:

1. Invoke `superpowers:writing-plans` to create a detailed implementation plan.
2. Implement in order: parser -> synthesizer -> verifier -> tests -> SKILL.md update.
3. Run integration test against actual Stage 1 artifacts.
4. Verify old shim scripts produce equivalent output.
