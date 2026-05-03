# ATDSL v0.7 Upgrade Report — Execution-Closure IR

## Goal

v0.7 upgrades the FIA Sink performance DSL from a field-completeness scaffold into an execution-closure scaffold. It absorbs high-value extraction artifacts that were not first-class in v0.6:

- test behavior contracts
- dataflow graphs
- memory lifetime contracts
- concrete workspace layout
- common memory-copy / GM format / offset rules
- common vector semantics
- split-core planner cost model
- learned patterns and negative lessons
- risk registry
- tunable knob domains

## Priority implementation

### P0 absorbed

1. `test_contract_ir`: maps changed DSL paths to UT/ST/benchmark surfaces.
2. `dataflow_ir`: explicit producer/consumer memory graph for GQA/MLA/FD flows.
3. `lifetime_ir`: L1/UB/GM workspace live ranges and reuse scopes.

### P1 absorbed

4. `workspace_ir`: concrete region formulas, producer/consumer functions, alias rules.
5. `memory_copy_ir`: GM formats, layout categories, offset calculators, copy helpers, ND-to-NZ lowering.
6. `vector_semantics_ir`: invalid-row correction, safe active token, repeat stride, FD merge helper semantics.
7. `split_core_planner_ir`: cost model, search bounds, sparse/sink handling, FD metadata production.

### P2 absorbed

8. `learning_ir`: learned patterns + negative lessons as graph-search priors and pruning rules.
9. `risk_ir`: risk-to-forbidden-transform/verifier/lowering guard mapping.
10. `knob_ir`: searchable knob domain separated from schedule points.

## Key files

- `ir/*_ir.schema.yaml`: new first-class IR schemas
- `runtime_ir/*.yaml`: source-backed runtime IR instances extracted from FIA Sink package
- `source_refs/stage1_*`: original extraction artifacts copied for provenance
- `schedule/schedule_points.yaml`: adds four guard-only schedule points and validator/test-selection links
- `scripts/lower_patch_plan.py`: now emits required tests, risk guards, lifetime/dataflow guards, and knob checks
- `scripts/validate_performance_dsl_v0_7.py`: package-level gate

## Still not done

v0.7 still does not generate a real AscendC `patch.diff`. The current chain is:

```text
transform_trace -> enriched patch_plan with execution-closure guards
```

The next milestone should be:

```text
patch_plan -> real source rewrite backend -> compile/correctness/benchmark -> execution_ir record
```
