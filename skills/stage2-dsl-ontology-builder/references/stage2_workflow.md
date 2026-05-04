# Stage 2 Workflow: From Stage 1 Artifacts to ATDSL Schema

## Purpose

Stage 2 transforms Stage 1 extraction outputs into a formal DSL ontology and schema for AscendC attention-operator performance tuning.

Stage 1 answers: what optimization facts exist in mature code?
Stage 2 answers: how should those facts become DSL modules, fields, validators, lowering passes, and searchable policies?

## Inputs

Expected Stage 1 input directory:

```text
stage1_outputs/
  annotations/
  cards/
  knobs/
  constraints/
  risks/
  evidence/
  auxiliary/
```

Key input types:

- Function annotations
- Optimization cards
- Tunable knobs
- Constraint lists
- Risk lists
- Source evidence
- Dataflow/pipeline/memory/workspace auxiliary views

## Output stages

### 1. Card canonicalization

Merge similar cards and normalize naming.

Example aliases:

```text
kv_l1_reuse
k_cache_l1
reuse_k_for_group
l1_kv_cache
```

Canonical card:

```text
l1_kv_residency_across_g
```

### 2. Module ontology

Group cards into DSL modules. Each module must have a clear responsibility.

Example:

```yaml
module: l1_residency
responsibility: Describe K/V tile residency in L1, reuse scope, prefetch, and eviction.
source_cards:
  - l1_kv_residency_across_g
hard_validators:
  - l1_capacity
  - l1_residency_loop_order
lowering_passes:
  - LowerL1Residency
```

### 3. Schema fields

For each module, define fields with type, candidates, edit policy, evidence, validators, and lowering consumers.

Bad field:

```yaml
memory_optimization: true
```

Good fields:

```yaml
l1_residency:
  objects:
    - name: k_tile
      residency_scope: across_g
      eviction: after_all_g_for_this_kv_block
```

### 4. Field policy

Classify every critical field:

- searchable
- configurable
- fixed
- forbidden

### 5. Validator specs

High-risk DSL fields must be guarded before later search/lowering.

Examples:

- L1 residency requires `l1_capacity` and `l1_residency_loop_order`.
- split-KV requires workspace no-alias and LSE merge validators.
- sparse window requires range and alignment validators.
- event dependency should be fixed/read-only in early versions.

### 6. Lowering pass specs

Define lowering pass interfaces, not full implementation.

A lowering pass must declare:

- consumes
- emits
- patch_points
- validators
- editable policy

### 7. Shadow DSL validation

Represent mature kernels using the schema. If mature code cannot be expressed, the schema is incomplete.

Generate at least:

- `fa_forward_shadow.yaml`
- `flash_decode_shadow.yaml`

## Suggested execution order

```text
Stage 1 artifacts
  -> canonical_optimizations.yaml
  -> modules.yaml
  -> schema/modules/*.yaml
  -> field_policy.yaml
  -> validators_spec/*.yaml
  -> lowering_spec/*.yaml
  -> examples/*_shadow.yaml
  -> review/*.md + quality_gate.json
```

## Stage 2 v0.4 four-layer contract

Stage 2 also emits four agent-facing layers:

- Semantic IR: pure operator meaning, shape, dtype, layout intent, and fixed formulas.
- Kernel IR: schedulable objects such as loops, tiles, buffers, memory scopes, and pipeline stages.
- Hardware contract: target-sensitive capacities, memory spaces, alignment, and intrinsic assumptions.
- Execution feedback: feature schema, metric schema, schedule trace, and tuning record format.
