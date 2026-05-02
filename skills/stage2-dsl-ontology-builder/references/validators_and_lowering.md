# Validators and Lowering Specs

## Validators

Validators are pre-lowering guards. They reduce compile failures, correctness bugs, and unsafe search moves.

### Mandatory validators

#### ub_capacity

Checks estimated UB allocation against target UB size.

#### l1_capacity

Checks enabled L1 regions, K/V ping-pong, scratch, and format expansion against target L1 size.

#### workspace_no_alias

Ensures workspace offsets are unique across logical indices such as batch, head, group, s1 segment, and split id.

#### sparse_window_alignment

Ensures S2 start/end are in bounds and aligned as required.

#### split_kv_lse_merge_valid

Ensures split-KV partial output/max/sum exist and use numerically stable online LSE merge.

#### event_dependency_valid

Ensures pipeline event/wait/flag dependencies are not broken. In early versions, event schedules should be read-only or chosen from fixed variants.

#### l1_residency_loop_order

Ensures `residency_scope: across_g` implies `decode.loop_order: kv_outer_g_inner` or an equivalent loop structure.

## Lowering pass specs

### LowerTiling

Consumes: `tiling`, `target`, `features`

Emits:

- host tiling fields
- constexpr constants
- tile-related guards

Patch points:

- host tiling function
- `ComputeConstexpr`

### LowerCoreMapping

Consumes: `core_mapping`, `shape`, `tiling`

Emits:

- blockIdx to logical-axis mapping
- split-factor logic

Patch points:

- `ComputeAxisIdx`
- process loop headers

### LowerSparseWindow

Consumes: `sparse_window`, `shape`, `features`

Emits:

- S2 start/end expressions
- alignment postprocess

Patch points:

- `GetS2LoopRange`

### LowerL1Partition

Consumes: `l1_partition`, `target`, `decode`, `tiling`

Emits:

- L1 region definitions
- TPipe/TBuf allocation plan
- capacity assertions

Patch points:

- `InitBuffer`
- buffer init helper

### LowerL1Residency

Consumes: `l1_residency`, `l1_partition`, `decode.loop_order`

Emits:

- K/V DataCopy placement
- reuse lifetime
- eviction points
- prefetch plan

Patch points:

- decode process loop
- KV tile load helpers

### LowerDecodeLoopNest

Consumes: `decode`, `core_mapping`, `l1_residency`

Emits:

- KV block loop
- group loop
- split-KV loop
- loop order selection

Patch points:

- `Process`

### LowerWorkspaceLayout

Consumes: `workspace`, `decode.split_kv`, `shape`

Emits:

- offset functions
- partial result layout
- no-alias assertions

Patch points:

- workspace offset functions
- `CalcAccumOffset`-like functions

### LowerPipeline

Consumes: `pipeline`, `memory`, `compute`

Emits:

- stage schedule
- limited event variants
- ring depth

Patch points:

- `Process`
- pipeline helper functions

In early versions, `LowerPipeline` should only lower fixed templates or limited variants, not arbitrary scheduling.
