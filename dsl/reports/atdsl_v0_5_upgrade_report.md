# ATDSL v0.5 Performance DSL Upgrade Report

## Goal

Convert the v0.4 Stage2 design artifact into a more complete **operator performance-optimization DSL scaffold**. The target is not a full general-purpose kernel DSL. The target is a DSL that lets an optimization agent safely search, validate, lower to patch plans, benchmark, and record feedback for existing AscendC kernels.

## Main changes

1. **Canonical path consistency**
   - Fixed `flash_decode.route.split_kv_enabled` path mismatch.
   - Added path convention rules to `schedule/schedule_points.yaml`.
   - Added validator logic to ensure schedule-point paths resolve in the example instance and match binding paths when binding is required.

2. **Example completeness**
   - Added missing `semantic_invariants` required by `semantic_ir.schema.yaml`.
   - Added `kernel_ir.flash_decode.route.split_kv_enabled.value`.
   - Added `kernel_ir.tiles.fd_g_s1_base_size`.
   - Added `kernel_ir.sparse_policy.s2_range_policy`.
   - Added `lowering_ir` and `execution_ir` placeholders to the example instance.

3. **Binding IR strengthening**
   - Added binding records for `workspace.flash_decode_regions` and `sparse.policy.s2_range`.
   - Added `binding_record_schema` and `minimum_review_policy`.
   - Added `bindings/candidate_symbol_binding.template.yaml`.
   - Added `bindings/reviewed_symbol_binding.example.yaml` for MVP tests.

4. **Lowering IR added**
   - Added `ir/lowering_ir.schema.yaml`.
   - Added `lowering/patch_plan.schema.yaml`.
   - Added `lowering/examples/patch_plan_try_s2_base_128.yaml`.
   - Enhanced `backend_contracts/ascendc_patch/backend_contract.yaml` with lowering pass contracts.

5. **Verifier strengthening**
   - Replaced empty hardware verifier with five validator definitions:
     - `ub_capacity`
     - `l1_capacity`
     - `s2_alignment`
     - `event_model_valid`
     - `engine_supported`

6. **Executable scaffolds**
   - Added `scripts/validate_performance_dsl.py`.
   - Added `scripts/transform_apply.py`.
   - Added `scripts/lower_patch_plan.py`.
   - Updated `scripts/validate_optimized_dsl.py` to forward to the stronger v0.5 validator.

7. **Domain extension separation**
   - Added `extensions/attention_extension_ir.schema.yaml` to separate attention-specific fields from the base optimization DSL direction.

## Validation result

```text
PASS ATDSL v0.5 performance DSL MVP checks
schedule_points=7 semantic_bindings=8 hardware_validators=5
```

## MVP lowering smoke test

The transform:

```text
examples/transforms/try_s2_base_128.yaml
```

can now be applied to:

```text
examples/fused_infer_attention_sink_atdsl_v2.yaml
```

and lowered to a patch plan using:

```text
bindings/reviewed_symbol_binding.example.yaml
```

Result:

```text
patch_plan_transform_try_s2_base_128
rewrite_units=1
semantic_id=attention.tiling.s2_base
rewrite_kind=replace_expr
new_value=128
status=patch_plan_only_not_source_diff
```

## Remaining limitations

This package still does **not** implement real AscendC source diff generation. It emits reviewable patch plans. The production next step is to connect `patch_plan.yaml` to a real AST/text rewrite backend and replace example bindings with source-evidence-based reviewed bindings.

## Recommended next milestone

Run one full optimization loop end to end:

```text
sp_tiling_s2_base
  -> transform_trace
  -> transform_apply
  -> verifier
  -> reviewed binding
  -> patch_plan
  -> real AscendC patch.diff
  -> compile
  -> correctness
  -> benchmark
  -> execution_ir record
```
