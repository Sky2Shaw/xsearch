# ATDSL Stage2 Deep Optimization Report

## Summary

The previous Stage2 DSL was strong at capturing optimization knowledge, but it was not yet an agent-ready compiler protocol. This optimized package upgrades it into a four-layer design:

```text
semantic_ir
  -> kernel_ir
  -> hardware_contract_ir
  -> execution_ir
```

It also adds:

```text
schedule_points
transform_trace
binding_ir
layered_verifier
backend_contracts
feature_schema
profiles
migration map
```

## Main improvements

### 1. Flat schema -> four-layer IR

The old modules `shape_layout`, `tiling`, `pipeline`, `memory`, `workspace`, `flash_decode`, `sparse_policy`, and `compute` are now assigned to the correct IR layer. This prevents semantic invariants from being mixed with searchable schedule choices.

### 2. Field search -> schedule point search

Searchable knobs such as `s2BaseSize` and `mBaseSize` are no longer just fields. They become explicit schedule points with action type, candidates, validators, binding requirements, and source evidence.

### 3. Delta -> transform trace

An agent should emit transform traces such as `transform_enable_l1_v_reuse_across_g`, not raw full-DSL rewrites. Transform traces preserve intent, preconditions, mutations, expected effects, risks, and validators.

### 4. Variable-name lowering -> semantic binding

The previous lowering intent could mention concrete variable names such as `s2BaseSize`. This is not portable across kernels. The optimized design introduces `binding_ir`, where lowering depends on semantic fields such as `attention.tiling.s2_base` and a reviewed symbol binding map.

### 5. Validators -> layered verifier

Validator seeds are grouped into semantic/kernel/hardware/lowering/numerical layers. This makes validation reports more actionable and gives the search planner a better reason for rejection.

### 6. AscendC-only lowering -> backend contracts

The optimized DSL defines separate backend contracts for:

- `ascendc_patch`
- `mskpp_model`
- `static_cost_model`

This allows candidate pre-ranking before expensive compile/benchmark.

## Important preserved decisions

- `flash_decode.metadata_bridge` remains the canonical owner of FD metadata.
- `split_core.range_contract` is a producer/range contract and does not redefine FD metadata.
- `scalar.offset_rules` consumes metadata and should not duplicate ownership.
- MLA tail regions keep `binding_status`; host-budget-only stubs must not be lowered as standalone GM regions.
- Pipeline event reordering remains forbidden by default.

## Stage readiness

This package is ready to be used as the improved Stage2 design input for Stage3.5 and Stage4.

It is **not** a real AscendC patch generator yet. Real lowering requires `reviewed_symbol_binding.yaml`.
