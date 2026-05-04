# Recommended fixes — `ai_infra_fused_infer_attention_sink` Stage-1

Stage-1 is **READY_FOR_STAGE2** with **0 blocking findings**. The items below are quality-of-life improvements, not gate failures. Stage-2 may proceed in parallel.

## Priority 1 — Stage-2 ingestion-time guardrails

These are not Stage-1 fixes; they are guardrails Stage-2 should add as it ingests the cards.

### G1. Add a negative-evidence regression test for MLA workspace tail stubs

**Why:** `OC-WORKSPACE-MLA-NUPDATE-BUDGET-STUB` and `OC-WORKSPACE-MLA-SOFTMAX-SUM-BUDGET-STUB` carry confidence `medium` because they assert the *absence* of a dedicated kernel `SetGlobalBuffer` for the tail bytes. The forbidden transform `FT-NO-LOWER-MLA-BUDGET-TAIL-AS-BOUND-GM` codifies the rule, but a future kernel patch could silently bind a new GM tensor and invalidate the alias-only lowering.

**Action:** Stage-2 schema should include a validator pass that scans `op_kernel/fia_kernel_nonquant_mla_sink.h::InitWorkspace` and any MLA Vec1/Vec2 file for `SetGlobalBuffer` calls referencing a workspace offset between `vec2ResGm` end and `accumOutGm` start. If any new binding appears, fail the validator and require an explicit re-classification of these cards.

### G2. Lower hardware micro-optimization cards as policy tables

**Why:** `OC-COMMON-MATMUL-UNITFLAG-K-LOOP` (unitFlag = 0/2/3), `OC-COMMON-VECTOR-REPEAT-STRIDE-THRESHOLD` (2048-element threshold), `OC-COMMON-ND2NZ-INT4-STRIDE-LIMIT-FALLBACK` (HALF_SIZE_DIVISOR fallback), and `OC-COMMON-FIA-TILING-SHAPE-NZ-PACKING` (D0=16) all encode rules that depend on dtype × tile-size × layout. The card prose is correct but compressed.

**Action:** Stage-2 should represent the dispatch as policy tables rather than as a single scalar field, so that future operator additions can opt into different combinations without rewriting the rule.

## Priority 2 — Stage-1 follow-ups (post-Stage-2 schema lock)

These are Stage-1 artifact tightening items that should be tracked but do not need to be fixed before Stage-2 begins.

### S1. SE-* id catalogue cross-reference

**Why:** Cards reference source-evidence ids (SE-*) that resolve through `cross_reference.yaml` to `evidence/source_evidence.yaml`. The SE-* id catalogue is implicit; explicitly publishing the id-to-file-line mapping in a single file would simplify Stage-2 ingestion auditing.

**Action:** Optionally generate a flat `evidence/source_evidence_id_index.yaml` that lists every SE-* id with its file, line range, and short description. Cards would not need to change.

### S2. Confidence-rating audit

**Why:** Two cards carry `confidence: medium`. The rest are `high`. There is no formal rubric for the medium tag besides "negative-evidence asymmetry". Other potentially-medium cards (e.g., common-layer hardware cards whose applicability bands depend on operator-external constants) might benefit from explicit downgrade.

**Action:** Stage-2 schema should reflect the `confidence` field directly as a column on each ingested entity, so Stage-2 validators can weight `medium` entries differently from `high` entries.

### S3. Section 9 (Common Infrastructure) granularity

**Why:** Section 9 mixes matmul micro-ops, vector micro-ops, buffer policy, ND2NZ packing, and FiaTilingShape NZ packing into one section. Stage-2 will likely split this across multiple modules.

**Action:** Optionally re-section 9 into 9a (matmul), 9b (vector), 9c (buffer), 9d (memcpy/format) for cleaner ingestion. Not required.

## Items deliberately not flagged

- **Internal split-core planner is external** — correctly noted in `dsl/split_core_range_contract.yaml`. No fix needed.
- **8 schema gaps with `ready_for_ingestion` stubs** — these are Stage-2 ingestion targets, not Stage-1 holes. The `temporary_schema_stub` artifacts are sufficient.
- **`R-SHAPE-LAYOUT-CONTRACT-DRIFT` has no `related_forbidden_transform_ids`** — correct, because shape/layout drift is a co-design concern rather than an enforceable single-direction transform constraint.
