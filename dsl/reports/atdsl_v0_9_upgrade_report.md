# ATDSL v0.9 Upgrade Report — Card-driven DSL Execution

## Goal

v0.8 reorganized optimization cards by execution flow. v0.9 makes those cards executable by adding a formal card-to-DSL mapping layer.

## Main changes

1. Added `ir/card_to_dsl_mapping.schema.yaml`.
2. Added `runtime_ir/card_to_dsl_mapping.fia_sink.yaml` with one mapping for every optimization card.
3. Added `ir/tiling_ir.schema.yaml` and `runtime_ir/tiling_ir.fia_sink.yaml` to make Tiling/SplitCore cards generate schedule-point candidates rather than only describe strategy.
4. Added `runtime_ir/card_driven_schedule_selection.fia_sink.yaml` for profile -> flow_group -> card -> schedule_point -> transform selection.
5. Updated `schedule/schedule_points.yaml` with `flow_group`, `source_cards`, and card-driven selection metadata.
6. Added 7 guard/contract schedule points for the v0.8 cards that were previously not executable:
   - `sp_gqa_c1_q_l1_snapshot_policy`
   - `sp_mla_mm1_rope_nope_packing_guard`
   - `sp_vec1_sink_softmax_contract`
   - `sp_v2_layout_aware_output_lse_copyout_guard`
   - `sp_host_contiguous_int4_metadata_guard`
   - `sp_host_softmax_lse_zero_placeholder_guard`
   - `sp_fd_blockidx_task_mapping_guard`
7. Updated `scripts/lower_patch_plan.py` so it can resolve `card_id` and attach card-derived tests, verifiers, risks, dataflow guards, lifetime guards, and candidate-generation metadata.

## Current capability

The chain now supports:

```text
profile/bottleneck
  -> flow_group
  -> card_id
  -> card_to_dsl_mapping
  -> schedule_point
  -> transform_trace
  -> card-aware patch_plan
```

The package still does not implement real AscendC `patch.diff` generation. It emits structured patch plans and execution guards.

## Validation

Run:

```bash
python scripts/validate_performance_dsl_v0_9.py
```

Expected:

```text
PASS ATDSL v0.9 card-driven execution checks
```
