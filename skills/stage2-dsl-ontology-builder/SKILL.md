---
name: stage2-dsl-ontology-builder
description: Use this skill when converting Stage 1 AscendC FlashAttention/FlashDecode extraction outputs into Stage 2 ATDSL ontology, schema modules, validators, lowering specs, shadow DSL examples, and a review gate. Trigger when the user asks for Stage 2 DSL design, ontology/schema generation, card-to-field mapping, validator/lowering specs, or shadow DSL validation from Stage 1 artifacts.
---

# Stage 2 ATDSL Ontology Builder

You are building Stage 2 for an AscendC attention-operator performance-tuning DSL. Stage 1 has extracted facts from mature AscendC FlashAttention / SFA / FlashDecode implementations. Your job is to transform those facts into a formal DSL ontology, schemas, validator specifications, lowering specifications, and shadow DSL examples.

## Core principle

Do not invent a general-purpose language. Build a narrow, evidence-backed **ATDSL = Ascend Attention Tuning DSL** for performance search and later lowering.

Stage 2 consumes Stage 1 artifacts:

- `function_annotation`: what functions do, inputs/outputs, memory behavior, pipeline role, risks.
- `optimization_card`: canonical optimization patterns, preconditions, risks, candidate DSL fields.
- `tunable_knobs`: fields that can be searched.
- `constraints`: hard rules that must be validated before compile/lowering.
- `risks`: correctness/performance failure modes that require guards.
- `source_evidence`: file/function/behavior evidence backing each field.
- Optional: dataflow graphs, pipeline graphs, memory lifetime, workspace layout.

Stage 2 produces:

- canonical optimization ontology
- module list
- per-module schema
- field policy: searchable/configurable/fixed/forbidden
- validator specs
- lowering pass specs
- shadow DSL examples
- schema review and missing-field report

## Required output directory

Default output directory: `stage2_outputs/`

Create this structure unless the user asks otherwise:

```text
stage2_outputs/
  ontology/
    modules.yaml
    canonical_optimizations.yaml
    field_policy.yaml
    card_to_module_matrix.md

  schema/
    atdsl.schema.yaml
    modules/
      kernel.schema.yaml
      target.schema.yaml
      features.schema.yaml
      interface.schema.yaml
      shape.schema.yaml
      tiling.schema.yaml
      core_mapping.schema.yaml
      memory.schema.yaml
      l1_partition.schema.yaml
      l1_residency.schema.yaml
      workspace.schema.yaml
      pipeline.schema.yaml
      decode.schema.yaml
      sparse_window.schema.yaml
      compute.schema.yaml
      tail_policy.schema.yaml
      search.schema.yaml
      lowering.schema.yaml

  validators_spec/
    ub_capacity.yaml
    l1_capacity.yaml
    workspace_no_alias.yaml
    sparse_window_alignment.yaml
    split_kv_lse_merge_valid.yaml
    event_dependency_valid.yaml
    l1_residency_loop_order.yaml

  lowering_spec/
    LowerTiling.yaml
    LowerCoreMapping.yaml
    LowerSparseWindow.yaml
    LowerL1Partition.yaml
    LowerL1Residency.yaml
    LowerDecodeLoopNest.yaml
    LowerWorkspaceLayout.yaml
    LowerPipeline.yaml

  examples/
    fa_forward_shadow.yaml
    flash_decode_shadow.yaml
    sfa_shadow.yaml

  review/
    schema_review.md
    coverage_matrix.md
    missing_fields.md
    quality_gate.json
```

## Workflow

### Step 0: Load only relevant references

Read these files in this skill as needed:

- `references/stage2_workflow.md` for the full workflow.
- `references/output_contract.md` for required files and formats.
- `references/schema_design_rules.md` for field design rules.
- `references/validators_and_lowering.md` for validator and lowering spec requirements.
- `references/quality_gate.md` for review criteria.

If scripts are available, use them to create initial skeletons, then refine manually based on Stage 1 artifacts.

### Step 1: Inspect Stage 1 inputs

Default input directory: `stage1_outputs/`.

Check for:

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

If artifacts are not split by directory, scan all YAML/JSON/Markdown under the input directory and infer roles.

### Step 2: Canonicalize optimization cards

Cluster and merge similar Stage 1 cards. Each canonical optimization must have:

- `id`
- `aliases`
- `intent`
- `applies_to`
- `preconditions`
- `risks`
- `required_dsl_modules`
- `suggested_fields`
- `searchable_knobs`
- `validators`
- `lowering_passes`
- `source_evidence`

Important canonical optimizations for AscendC attention DSL include:

- `fa_s1s2_tiling`
- `bmm1_vec1_bmm2_vec2_pipeline`
- `sparse_window_range_alignment`
- `workspace_no_alias_layout`
- `scalar_offset_hoist`
- `tail_duplicate_mask`
- `l1_kv_residency_across_g`
- `l1_partition_policy`
- `decode_kv_streaming_loop`
- `paged_kv_cache_addressing`
- `split_kv_lse_merge`
- `event_wait_flag_dependency`

### Step 3: Build DSL ontology modules

Create `ontology/modules.yaml`. Each module must declare:

- `name`
- `responsibility`
- `source_cards`
- `core_fields`
- `searchable_fields`
- `hard_validators`
- `lowering_passes`
- `profile_scope` such as `fa_forward`, `flash_decode`, `sfa`, `all`

Default module set:

```text
kernel, target, features, interface, shape, layout, tiling, core_mapping,
memory, l1_partition, l1_residency, workspace, pipeline, decode,
sparse_window, compute, tail_policy, constraints, search, lowering
```

### Step 4: Define schemas

Create one schema per module under `schema/modules/`. Every field must include:

- `type`
- `default` when meaningful
- `enum` or `candidates` when constrained
- `searchable: true|false`
- `editable_policy: searchable|configurable|fixed|forbidden`
- `source_cards`
- `source_evidence`
- `related_validators`
- `lowering_consumers`

Use structured YAML. Do not leave critical fields as vague text like `optimization: true`.

### Step 5: Define searchable field policy

Create `ontology/field_policy.yaml`. Classify fields as:

- `searchable`: agent may automatically search, for example `tiling.s1_base`, `decode.kv_block`, `decode.split_kv.num_splits`.
- `configurable`: agent may modify with validators, for example `decode.loop_order`, `l1_partition.policy`.
- `fixed`: represent code facts but do not search, for example `compute.online_softmax.formula`.
- `forbidden`: do not modify in current version, for example arbitrary event reordering or dtype semantics.

### Step 6: Define validators

Every high-risk card must have at least one validator spec. Each validator file must include:

- `name`
- `module`
- `severity: hard|soft`
- `inputs`
- `expr`
- `error_message`
- `related_risks`
- `source_cards`
- `source_evidence`

Mandatory validators:

- `ub_capacity`
- `l1_capacity`
- `workspace_no_alias`
- `sparse_window_alignment`
- `split_kv_lse_merge_valid`
- `event_dependency_valid`
- `l1_residency_loop_order`

### Step 7: Define lowering pass specs

Do not implement full lowering yet. Define specs. Each lowering pass must include:

- `name`
- `consumes`
- `emits`
- `patch_points`
- `pre_validators`
- `post_validators`
- `editable_policy`
- `source_cards`

Mandatory passes:

- `LowerTiling`
- `LowerCoreMapping`
- `LowerSparseWindow`
- `LowerL1Partition`
- `LowerL1Residency`
- `LowerDecodeLoopNest`
- `LowerWorkspaceLayout`
- `LowerPipeline`

### Step 8: Generate shadow DSL examples

Generate at least two shadow examples:

- `examples/fa_forward_shadow.yaml`
- `examples/flash_decode_shadow.yaml`

If Stage 1 includes SFA cards, also generate `examples/sfa_shadow.yaml`.

Shadow DSL is a read-only representation of mature code. It must prove the schema can express existing mature implementations before search/lowering starts.

### Step 9: Review and quality gate

Create:

- `review/schema_review.md`
- `review/coverage_matrix.md`
- `review/missing_fields.md`
- `review/quality_gate.json`

Quality gate must check:

- every module maps to at least one card
- every important field has evidence
- every searchable knob has candidates/range
- every high-risk card has validator coverage
- every lowering pass has consumes/emits/patch_points
- at least two mature kernels can be represented as shadow DSL
- shadow DSL covers at least 80% of key optimization structures

## Recommended scripts

If present, run:

```bash
python scripts/bootstrap_stage2.py --input stage1_outputs --output stage2_outputs
python scripts/check_stage2_quality.py --input stage2_outputs
```

After scripts run, manually refine the generated files using Stage 1 evidence. The scripts are scaffolding, not final truth.

## Hard constraints for your own behavior

- Do not invent unsupported DSL fields without marking them as `needs_evidence: true`.
- Do not make event/wait reordering searchable in early versions.
- Do not make online softmax or LSE math formulas freely editable.
- Do not create L1 residency fields without loop-order and L1-capacity validators.
- Do not create split-KV fields without partial workspace and LSE merge validators.
- Do not allow workspace-related fields without no-alias constraints.
- Prefer a small, high-quality schema over a large vague schema.

## Final response to user

When done, summarize:

1. files created
2. quality gate result
3. missing fields or weak evidence
4. next recommended step: implement validators or create lowering MVP
