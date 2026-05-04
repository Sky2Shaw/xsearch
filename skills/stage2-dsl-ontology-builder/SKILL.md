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

In addition to the artifact directories, the pipeline produces:
- `stage2_outputs/.evidence_graph.json` — the typed EvidenceGraph intermediate representation.

Create this structure unless the user asks otherwise:

```text
stage2_outputs/
  ontology/
    modules.yaml
    canonical_optimizations.yaml
    field_policy.yaml
    card_to_module_matrix.md

  ir/
    semantic_ir.yaml
    kernel_ir.yaml
    hardware_contract.yaml
    execution_feedback.yaml

  search/
    schedule_space.yaml
    feature_schema.yaml
    measurement_schema.yaml
    tuning_record.schema.yaml

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
    agent_readiness.md
```

## Workflow

### Step 0: Load references (unchanged)

Read these files as needed:
- `references/stage2_workflow.md`
- `references/output_contract.md`
- `references/schema_design_rules.md`
- `references/validators_and_lowering.md`
- `references/quality_gate.md`

### Step 1: Parse Stage 1 inputs into EvidenceGraph

```bash
python scripts/stage2_parser.py --input stage1_outputs --output stage2_outputs/.evidence_graph.json
```

This creates a typed graph of all cards, constraints, risks, evidence, knobs, pipeline nodes, and workspace regions with cross-reference edges.

### Step 2: Synthesize Stage 2 artifacts

```bash
python scripts/stage2_synthesizer.py --evidence-graph stage2_outputs/.evidence_graph.json --output stage2_outputs
```

This traverses the EvidenceGraph to infer modules, generate schemas, derive validators, and emit shadow DSL.

### Step 3: Run semantic quality gate

```bash
python scripts/stage2_verifier.py --evidence-graph stage2_outputs/.evidence_graph.json --stage2-dir stage2_outputs
```

This checks evidence connectivity, field completeness, knob mapping, validator coverage, lowering spec clarity, and shadow DSL coverage.

### Step 4: Manual refinement

The synthesizer generates evidence-driven scaffold. Codex should review:
- Fields marked `needs_evidence: true`
- Validators with placeholder `expr`
- Shadow DSL coverage gaps
- Module inference flagged as `needs_review`

Refine by updating Stage 1 artifacts and re-running the pipeline, or by editing `scripts/module_inference_rules.yaml`.

## Deprecated but preserved

```bash
python scripts/bootstrap_stage2.py --input stage1_outputs --output stage2_outputs  # delegates to parser + synthesizer
python scripts/check_stage2_quality.py --input stage2_outputs                     # delegates to verifier
```

## Hard constraints for your own behavior

- Do not invent unsupported DSL fields without marking them as `needs_evidence: true`.
- Do not make event/wait reordering searchable in early versions.
- Do not make online softmax or LSE math formulas freely editable.
- Do not create L1 residency fields without loop-order and L1-capacity validators.
- Do not create split-KV fields without partial workspace and LSE merge validators.
- Do not allow workspace-related fields without no-alias constraints.
- Prefer a small, high-quality schema over a large vague schema.
- Treat v0.4 artifacts as contracts, not executable compiler output.
- Every searchable field must appear in `search/schedule_space.yaml` with a finite domain and validator guard.
- Every schedule point must be guarded by a constraint, risk-derived validator, or mandatory validator.
- Hardware-sensitive fields must link to `ir/hardware_contract.yaml`.
- Tuning records must include environment fingerprint, shape signature, DSL version, schedule trace, validation result, compile result, measurement result, and failure metadata.
- Do not claim benchmark results from `measurement_schema.yaml`; it describes future measurements only.

## Final response to user

When done, summarize:

1. files created
2. quality gate result
3. missing fields or weak evidence
4. next recommended step: implement validators or create lowering MVP
