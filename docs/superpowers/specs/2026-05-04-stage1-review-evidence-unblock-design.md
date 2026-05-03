# Stage-1 Review Evidence Unblock Design

## Context

The current Stage-1 review for `artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction` scores 84/100 with readiness `READY_WITH_FIXES`. The main blocker is traceability: 15 of 33 optimization cards cite source evidence IDs that are not defined in `evidence/source_evidence.yaml`.

The user selected the complete evidence repair approach: fill every unresolved source evidence ID, rerun the review context, and rescore based on the repaired artifacts.

## Goal

Repair the Stage-1 artifact evidence chain so all optimization cards have resolvable source evidence and the Stage-2 readiness gate is no longer blocked by card evidence coverage.

Success criteria:

- All 33 optimization cards have resolvable `source_evidence[].id` entries.
- Important card evidence coverage is 33/33, or 100%.
- `prepare_review_context.py` runs successfully after the evidence repair.
- Updated review files report a gate-pass state for card evidence coverage.
- Target score is 93+ and readiness is `READY_FOR_STAGE2` if source spot checks support that judgement.

If any card claim is not supported by source, the review must report the lower score and remaining issue rather than forcing 93+.

## Scope

In scope:

- Add missing evidence records to `artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction/evidence/source_evidence.yaml`.
- Use exact source-backed evidence with `id`, `artifact_ids`, `file`, `symbol`, `line_range`, `observed_fact`, and `confidence`.
- Use operator source under `/mnt/workspace/omni-ops-performance/inference/ascendc/src/ops-transformer/attention/ai_infra_fused_infer_attention_sink` for operator-specific cards.
- Use common helper source under `/mnt/workspace/omni-ops-performance/inference/ascendc/src/ops-transformer/attention/common` for common-helper cards.
- Rerun `prepare_review_context.py`.
- Update `stage1_review/score_report.md`, `scorecard.yaml`, `blocking_findings.yaml`, `missing_patterns.yaml`, `recommended_fixes.md`, and `stage2_readiness.yaml` based on the verified result.

Out of scope:

- Modifying AscendC operator source.
- Rewriting optimization-card semantics unless a claim is contradicted by source.
- Regenerating or editing Stage-2 schema artifacts under `.xperf_atdsl_stage2`.
- Inflating the score without source-backed evidence.

## Evidence Repair Strategy

Add records for all currently missing evidence IDs:

- `SE-GQA-KP-L1-PINGPONG`
- `SE-GQA-KP-L1-EVENT-CYCLE`
- `SE-MM1-VEC1-BRIDGE-PIPELINE`
- `SE-MM1-VEC1-SINK-SKIP`
- `SE-MM1-SPARSE-SKIP-SETFLAG`
- `SE-MM1-SPARSE-SKIP-ISCAL`
- `SE-MM1-OUTPUT-ATOMIC-ADD`
- `SE-MM1-K-SPLIT-FIXPIPE`
- `SE-VEC1-SOFTMAX-FLASHV2`
- `SE-VEC1-SOFTMAX-FIRST-LOOP`
- `SE-SOFTMAX-TILING-FUNC`
- `SE-SOFTMAX-BRC-CONFIG`
- `SE-VEC1-SINK-SKIP-STATE`
- `SE-VEC1-SINK-VALUE-MIN`
- `SE-VEC1-INVALID-ROW-ZERO`
- `SE-VEC1-M-PARTITION-FORMULA`
- `SE-VEC1-NBUFFER-VEC-DEAL`
- `SE-LSE-COMPUTE-SOFTMAX`
- `SE-LSE-ADJUST-INVALID`
- `SE-LSE-EXPORT-LAYOUT`
- `SE-LSE-EXPORT-TND`
- `SE-LSE-EXPORT-BSND`
- `SE-LSE-EXPORT-BNSD`
- `SE-COMMON-MATMUL-UNITFLAG`
- `SE-COMMON-MATMUL-K-LOOP`
- `SE-COMMON-VECTOR-REPEAT-STRIDE`
- `SE-COMMON-VECTOR-PIPE-V-BARRIER`
- `SE-COMMON-BUFFER-MATRIX-2X2`
- `SE-COMMON-BUFFER-PEEK-NEXT-K`
- `SE-COMMON-ND2NZ-INT4-DIVISOR`
- `SE-COMMON-ND2NZ-STRIDE-LIMIT`
- `SE-COMMON-FIA-TILING-AXIS-MAP`
- `SE-COMMON-FIA-TILING-D-FALLBACK`

When one source region supports multiple IDs, each evidence record should still state the specific observed fact for that ID. For example, a buffer ping-pong ID and an event-cycle ID may point to overlapping lines, but their `observed_fact` fields should focus on different guarantees.

## Verification Design

Run these checks after editing:

1. Parse all edited YAML files.
2. Confirm every optimization-card `source_evidence[].id` exists in `evidence/source_evidence.yaml`.
3. Confirm each newly added evidence `file` exists either under the operator source root or the common attention helper root.
4. Spot-check source lines for each evidence group.
5. Rerun:

```bash
python3 /home/developer/.codex/skills/stage1-artifact-scorer/scripts/prepare_review_context.py \
  --input artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction \
  --output artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction/stage1_review \
  --source-root /mnt/workspace/omni-ops-performance/inference/ascendc/src/ops-transformer/attention/ai_infra_fused_infer_attention_sink
```

6. Recompute the scorecard and gate results.

## Review Update Rules

If all evidence resolves and source spot checks pass:

- Set card evidence coverage to `33/33 = 100%`.
- Mark the evidence coverage gate as `PASS`.
- Remove the Stage-2 blocker for unresolved card evidence.
- Raise traceability and accuracy scores only to the degree supported by the verified source evidence.
- Set readiness to `READY_FOR_STAGE2` only if all gate conditions pass.

If any evidence cannot be verified:

- Keep the affected card marked as weak or suspicious.
- Keep readiness at `READY_WITH_FIXES`.
- Document the remaining issue in `blocking_findings.yaml` or `missing_patterns.yaml`.

## Risks

- A new evidence record may point to a nearby but insufficient source region. Mitigation: inspect the exact source snippet before writing the observed fact.
- Common-helper cards may use common source correctly, while operator-specific cards still need operator source. Mitigation: keep source roots separated by card type.
- Updating only review files would make the score look better without fixing traceability. Mitigation: repair `evidence/source_evidence.yaml` first, then regenerate review context.
- Existing Stage-2 artifacts may appear related but are out of scope. Mitigation: do not edit `.xperf_atdsl_stage2`.

## Deliverables

- Repaired `evidence/source_evidence.yaml`.
- Regenerated `stage1_review/evidence_pack.yaml`, `inventory.yaml`, `cross_reference.yaml`, and `source_spot_check_plan.yaml`.
- Updated score report and YAML gate outputs under `stage1_review/`.
- Final summary with evidence coverage before/after, score, readiness, and any residual risk.
