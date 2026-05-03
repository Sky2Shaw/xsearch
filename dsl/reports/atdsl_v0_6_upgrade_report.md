# ATDSL v0.7 Upgrade Report

## Goal

This version upgrades ATDSL from a v0.5 performance-DSL scaffold to a FIA Sink field-completeness candidate. It absorbs the eight Stage-1 schema gaps discovered from `ai_infra_fused_infer_attention_sink` source extraction.

## Priority-driven changes

| Priority | Gap | v0.7 change | Status |
|---|---|---|---|
| P0 | Real source binding | Added `bindings/reviewed_symbol_binding.fia_sink.yaml` with host/kernel evidence for tiling, FD metadata, scalar formulas, MLA nUpdate, workspace tail, sparse, shape/layout | Partial production-ready; source rewrites only for reviewed/high patch points |
| P1 | `flash_decode.fdparams.*` | Promoted metadata arrays to first-class `kernel_ir.flash_decode.fdparams` with producer/consumer contracts | Complete for contract/verifier; source rewrite forbidden |
| P2 | workspace and split-core contract | Added split-core range assignment contract, FD workspace region contracts, MLA budget-only tail region model | Complete as verifier/lowering guard |
| P3 | scalar offset rules | Added five scalar offset patterns from Stage-1 contract, including FD task offset and MLA reload/atomic offsets | Complete as reviewed formula bindings; source rewrite requires review |
| P4 | MLA nUpdate numeric contract | Added ordered micro-step contract, atomic target, broadcast group, `syncV1NupdateC2` constraint | Complete as numerical contract |
| P5 | shape/sparse contracts | Promoted shape-layout and sparse policy contracts from source_refs into instance fields | Partial; patch lowering requires semantic review |

## Key semantic shift

v0.7 separates three lowering classes:

```text
source_rewrite
  Reviewed/high binding + concrete patch_points required.

contract_guard_only
  Emits verifier guards and reports; no source diff.

scalar_formula_patch_requires_review
  Requires source binding + algebraic equivalence proof + specialist review.
```

This prevents the agent from treating all newly modeled fields as freely rewritable knobs.

## Remaining blockers

1. Real C++/AscendC source-diff backend is still not implemented.
2. UB/L1 byte estimation still needs shape-bucket-driven formulas.
3. Sparse and shape-layout rewrites remain semantic-review-only.
4. Scalar formula rewrites need an equivalence checker before unattended lowering.
5. `memory.l1_residency.v_tile.scope` is still validated-by-rules, not fully reviewed for automatic rewrite.
