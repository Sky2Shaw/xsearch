# ATDSL v0.8 Card Flow Taxonomy Upgrade Report

## Goal

v0.7 had useful optimization cards, but the card arrangement was still flat and somewhat hard for an agent to traverse. v0.8 reorganizes cards by the real FIA Sink execution flow:

```text
Host/API -> Tiling/SplitCore -> C1 -> V1 -> C2 -> V2 -> FlashDecode -> Workspace/Pipeline/Scalar/Common
```

This keeps the agent from mixing a host tiling planner rule, a V1 semantic guard, and a C2 rewrite candidate as if they were the same kind of optimization action.

## Result

- Total cards: 28
- New cards added: 11
- Tiling/SplitCore cards: 7
- Flow groups: 12

## New P0/P1 cards added

```text
OC-GQA-MM1-Q-L1-SNAPSHOT-REUSE
OC-MLA-MM1-ROPE-NOPE-L1-PACKING
OC-SHARED-VEC1-SINK-SOFTMAX-FUSION
OC-LAYOUT-AWARE-OUTPUT-LSE-COPYOUT
OC-HOST-API-CONTIGUOUS-AND-INT4-VIEW-METADATA
OC-HOST-OPTIONAL-SOFTMAX-LSE-ZERO-PLACEHOLDER
OC-FD-BLOCKIDX-TASK-MAPPING
```

## New Tiling/SplitCore cards

Tiling split-core logic is now treated as a first-class card family because it generates the candidate search space rather than merely validating a chosen tile size.

```text
OC-TILING-SPLIT-CORE-COST-TABLE
OC-TILING-USED-CORE-SEARCH-BOUNDS
OC-TILING-FD-GS1-PARTITION-SEARCH
OC-TILING-SPARSE-SINK-PRE-NEXT-TOKEN-RANGES
```

These cards correspond to:

- cost table construction from aligned M/S2 tile sizes
- min/max/usedCoreNum search and clamping
- FD gS1 partition and metadata bridge
- sparse/sink preToken/nextToken S2 range assignment

## Agent usage policy

- `planner_*` cards generate or prune candidates; they should not directly patch source alone.
- `host_guard`, `semantic_vector_contract`, and `layout_copy_contract` are guard-first.
- `optimization_pattern` cards can propose source rewrites only after binding, lowering, verifier, and required tests are attached.

## Files changed

```text
source_refs/cards__optimization_cards.yaml
ir/card_ir.schema.yaml
runtime_ir/card_flow_taxonomy.fia_sink.yaml
reports/card_coverage_matrix_v0_8.yaml
scripts/validate_performance_dsl_v0_8.py
```
