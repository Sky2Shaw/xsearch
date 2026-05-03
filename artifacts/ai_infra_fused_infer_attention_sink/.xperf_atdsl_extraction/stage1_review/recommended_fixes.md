# Recommended Fixes

## Priority 1: Stage-2 Ingestion

The Stage-2 card evidence gate now passes: all 33 optimization cards have resolvable source evidence IDs.

Consume immediately:

- all 33 optimization cards with resolvable source evidence
- `workspace_layout.yaml`
- `pipeline_graphs.yaml`
- `dataflow_graphs.yaml`
- `memory_lifetime.yaml`
- constraints/risks with source-backed IDs
- knobs with source evidence

## Priority 2: Minor Follow-Ups

- Add `source_evidence_ids` to `C-TEMPLATE-IDENTITY`.
- Add or explicitly waive forbidden transforms for:
  - `R-SHAPE-LAYOUT-CONTRACT-DRIFT`
  - `R-COMMON-SHAPE-LAYOUT-VALIDATION-OMITTED`
- Treat index-only helper records as inventory unless Stage-2 needs their behavior.

## Priority 3: Re-run The Review Context

Re-run the review context after any future artifact edits:

```bash
python3 /home/developer/.codex/skills/stage1-artifact-scorer/scripts/prepare_review_context.py \
  --input artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction \
  --output artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction/stage1_review \
  --source-root /mnt/workspace/omni-ops-performance/inference/ascendc/src/ops-transformer/attention/ai_infra_fused_infer_attention_sink
```

Then recompute card count, resolvable evidence coverage, gate results, and scorecard.
