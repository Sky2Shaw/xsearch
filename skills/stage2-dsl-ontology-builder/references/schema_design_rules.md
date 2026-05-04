# ATDSL Schema Design Rules

## Scope

ATDSL is not a replacement for AscendC. It is an optimization-intent IR for attention-like operators.

It should express:

- shape/layout
- tiling
- core mapping
- memory hierarchy
- L1 partition and residency
- workspace layout
- pipeline structure
- decode KV streaming
- sparse window
- online softmax/LSE behavior
- tail/alignment
- search knobs
- hard constraints
- lowering intent

## Field quality criteria

A good field is:

- specific enough to lower later
- backed by Stage 1 evidence or marked `needs_evidence`
- typed
- constrained by enum/range when possible
- assigned an edit policy
- connected to validators if high-risk
- connected to lowering pass consumers

## Edit policies

### searchable

May be mutated automatically by graph search.

Examples:

```text
tiling.s1_base
tiling.s2_base
decode.kv_block
decode.split_kv.num_splits
l1_residency.prefetch.distance
```

### configurable

May be changed only with validators and careful search strategy.

Examples:

```text
decode.loop_order
l1_partition.policy
l1_residency.objects.scope
```

### fixed

Represent code facts but do not modify automatically.

Examples:

```text
compute.online_softmax.formula
interface.inputs
interface.outputs
```

### forbidden

Not editable in current version.

Examples:

```text
pipeline.events arbitrary reorder
arbitrary dtype semantic change
unsafe online LSE rewrite
```

## Mandatory high-risk guards

- `l1_residency` requires `l1_capacity` and `l1_residency_loop_order`.
- `l1_partition` requires `l1_capacity`.
- `workspace` requires `workspace_no_alias`.
- `decode.split_kv` requires `split_kv_workspace_no_alias` and `split_kv_lse_merge_valid`.
- `sparse_window` requires range and alignment checks.
- `pipeline.events` should be fixed or limited variants in early versions.

## Recommended modules

- `kernel`
- `target`
- `features`
- `interface`
- `shape`
- `layout`
- `tiling`
- `core_mapping`
- `memory`
- `l1_partition`
- `l1_residency`
- `workspace`
- `pipeline`
- `decode`
- `sparse_window`
- `compute`
- `tail_policy`
- `constraints`
- `search`
- `lowering`

## v0.4 IR-layer metadata

Every generated field should declare an `ir_layer`.

- `semantic`: operator meaning and fixed math.
- `kernel`: schedulable implementation choices.
- `hardware`: target capability or capacity assumptions.
- `execution_feedback`: metric, feature, trace, or replay fields.
- `needs_review`: field exists but layer inference was not reliable.
