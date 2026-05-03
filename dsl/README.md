# xperf ATDSL v0.9 — FIA Sink Card-driven DSL Execution

v0.8 reorganized optimization cards by execution flow. v0.9 turns those cards into executable DSL entry points.

```text
profile/bottleneck
  -> flow_group
  -> card_id
  -> card_to_dsl_mapping
  -> schedule_point
  -> transform_trace
  -> card-aware patch_plan
```

## What changed from v0.8

- Added `runtime_ir/card_to_dsl_mapping.fia_sink.yaml`: every card now maps to DSL paths, schedule points, verifier IDs, required tests, dataflow/lifetime guards, and lowering policy.
- Added `runtime_ir/tiling_ir.fia_sink.yaml`: Tiling/SplitCore cards now define candidate-generation rules for `s2BaseSize`, `mBaseSize`, `gS1BaseSizeOfFd`, and sparse/sink ranges.
- Added `runtime_ir/card_driven_schedule_selection.fia_sink.yaml`: profile signal -> flow group -> card -> schedule point selection flow.
- Added 7 card-driven guard schedule points for C1, V1, V2, Host, and FlashDecode task mapping cards.
- Updated `scripts/lower_patch_plan.py` with `--card-id` support and card-derived tests/guards.
- Added `lowering/examples/patch_plan_card_driven_try_s2_base_128_v0_9.yaml`.

## Validate

```bash
python scripts/validate_performance_dsl_v0_9.py
```

Expected:

```text
PASS ATDSL v0.9 card-driven execution checks
```

## Current limitation

v0.9 still emits structured patch plans, not real AscendC `patch.diff`. The next step is implementing a source rewrite backend for `sp_tiling_s2_base`.
