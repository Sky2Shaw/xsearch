# Extraction Checklist

- [Interface](#interface)
- [Shape and Layout](#shape-and-layout)
- [Tiling](#tiling)
- [Core Mapping](#core-mapping)
- [Pipeline](#pipeline)
- [Memory](#memory)
- [L1](#l1)
- [FlashDecode](#flashdecode)
- [Sparse and Mask](#sparse-and-mask)
- [Workspace](#workspace)
- [Tail and Alignment](#tail-and-alignment)
- [Scalar Optimization](#scalar-optimization)
- [Synchronization](#synchronization)
- [Optimization Card Criteria](#optimization-card-criteria)

Use this checklist to avoid missing common attention-kernel evidence. Record `unknown` when the source does not expose an item.

## Interface

- Query, key, value, and output tensor pointers.
- Mask, pse, dropout, and optional auxiliary tensors.
- Actual sequence length inputs and varlen controls.
- Block table and KV cache inputs.
- Workspace pointer and workspace metadata.
- Tiling data structures and scalar fields.

## Shape and Layout

- Batch and sequence dimensions: `B`, `S1`, `S2`, `N`, `N2`, `G`, and `D`.
- Layout modes: `TND`, `BSH`, `BNSD`, `ND`, and `NZ`.
- Varlen behavior and actual sequence length indexing.
- GQA, MQA, and MLA handling.
- Axis mapping and batch/head/group indexing.

## Tiling

- `s1_base`, `s2_base`, `baseM`, `baseN`, and `baseK`.
- `kv_block`, `page_size`, and block-table derived ranges.
- `n_ratio`, split factor, and decode split configuration.
- Per-core tile count, loop count, and tail tile handling.
- Tiling constants computed by `ComputeConstexpr` or related helpers.

## Core Mapping

- `blockIdx` mapping to batch, head, group, S1 tile, S2 tile, and split index.
- Core range partitioning and balance strategy.
- Sparse or varlen range adjustment per core.
- Per-core output or workspace ownership.

## Pipeline

- BMM1, Vec1, BMM2, and Vec2 stage ordering.
- For every visible implementation variant, such as GQA, MLA, FlashDecode, and generic nonquant, identify separate stage functions instead of merging same-name template methods.
- Preserve template owner identity for stage functions, for example `FiaBlockCubeNonQuantGqa<...>::ComputeMm2` versus `FiaBlockCubeNonQuantMla<...>::ComputeMm2`.
- Deep-extract the main MM1 and MM2/PV implementation for each variant when present; wrapper functions are not enough when the body delegates to `ProcessMm1`, `ProcessMm2`, `IterateBmm1`, or `IterateBmm2`.
- Ring buffer depth and queue assignment.
- `taskId` use and stage-specific extra state.
- `extraInfo` propagation between stages.
- Producer and consumer relationships across TPipe queues.

## Memory

- GM, UB, L1, L0A, L0B, and L0C tensor movement.
- `DataCopy` calls and copy direction.
- `LocalTensor` and `GlobalTensor` construction.
- `TPipe`, `TBuf`, and `TQue` allocation.
- Workspace offsets and no-alias assumptions.
- Offset accumulation and address arithmetic.

## L1

- L1 partition strategy.
- K and V resident strategy.
- L1 reuse across BMM1 or BMM2.
- L1 residency conditions and eviction points.
- Interaction with sparse windows, split-KV, and decode.

## FlashDecode

- KV cache access pattern.
- Block table lookup and page-size behavior.
- Split-KV factor and split ownership.
- Partial max, partial sum, and partial output workspace.
- LSE merge logic and final output normalization.
- Decode-specific workspace and synchronization risks.

## Sparse and Mask

- Sparse S2 range calculation.
- Mask window, causal window, sliding window, or prefix behavior.
- PSE and mask application stage.
- Invalid region handling and fill values.
- Relationship between sparse ranges and softmax stability.

## Workspace

- Workspace size fields and offset formulas.
- Workspace layout for temporary scores, partial outputs, partial max/sum, LSE, and split data.
- Workspace no-alias evidence.
- Per-core, per-batch, per-head, or per-split stride.
- Lifetime of each workspace region.

## Tail and Alignment

- S1, S2, D, and split tails.
- Alignment conditions for GM, UB, L1, and L0 copies.
- Tail masks and padding strategy.
- Vector tail handling and scalar fallback paths.
- Address alignment assumptions.

## Scalar Optimization

- Repeated div/mod calculations.
- Offset accumulation replacing repeated address recomputation.
- Constexpr precomputation and cached scalar fields.
- Loop-invariant calculations.
- Tradeoff between register pressure, scalar computation, and memory traffic.

## Synchronization

- `WaitFlag` and `SetFlag` use.
- MTE2 and MTE3 event ordering.
- Queue allocation, enqueue, dequeue, and free order.
- Cross-stage hazards and buffer reuse hazards.
- Barriers or implicit synchronization assumptions.

## Optimization Card Criteria

Create an optimization card when at least two of these are true:

- Performance relevance.
- Reusable pattern.
- Tunable parameter.
- Hard constraint.
- Correctness risk.
- DSL mapping.
- Lowering impact.
- Stable mature-code pattern.

Do not create an optimization card for:

- Trivial wrappers with no independent behavior.
- One-off details with no reuse signal.
- Unsupported guesses or inferred intent without code evidence.
- Basic field extraction that is already captured in a schema entry.
- Behavior whose only evidence is a name match without supporting code.
