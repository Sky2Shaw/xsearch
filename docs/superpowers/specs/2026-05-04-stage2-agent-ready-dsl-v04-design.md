# Stage 2 Agent-Ready DSL v0.4 Design

Date: 2026-05-04
Skill: stage2-dsl-ontology-builder
Status: design approved

## Context

`stage2-dsl-ontology-builder` already has an evidence-driven v0.3 pipeline:

```text
Stage 1 YAML -> EvidenceGraph -> Synthesizer -> Semantic Verifier -> stage2_outputs
```

That pipeline fixed the earlier template-driven weakness by preserving Stage 1 evidence and checking generated Stage 2 artifacts semantically. The new deep research report in `docs/superpowers/dsl_deep_report.md` points to the next gap: a DSL for an operator optimization agent should not only produce schema fields. It should expose a compiler protocol that is expressible, transformable, verifiable, measurable, learnable, and replayable.

This design upgrades Stage 2 to v0.4 by adding agent-ready DSL contracts while preserving the existing v0.3 pipeline and output paths.

## Problem Statement

The current Stage 2 skill can generate:

- optimization ontology
- module schemas
- field policies
- validators
- lowering specs
- shadow DSL examples
- semantic quality gate output

It does not yet make the following first-class:

- semantic IR boundaries separate from schedule decisions
- schedulable kernel IR objects such as loop, tile, buffer, thread, and intrinsic placeholders
- hardware capability contracts for target-sensitive legality and lowering
- schedule/search spaces that are guarded by validators
- feature, measurement, and tuning-record schemas for agent feedback and replay

Without these contracts, later agents can see which fields exist, but they do not have a formal action space, hardware constraint model, measurement protocol, or replay format.

## Goals

- Add Stage 2 v0.4 artifacts for four DSL layers: semantic IR, kernel IR, hardware contract, and execution feedback.
- Add search-space and tuning-record contracts that turn searchable fields into guarded agent actions.
- Extend generated schema fields with IR-layer and feedback metadata.
- Extend the verifier with an `agent_readiness` quality section.
- Preserve backward compatibility for existing output directories, legacy quality scores, and shim entrypoints.
- Keep scope limited to schema and contract generation. This stage does not implement a compiler backend, runtime profiler, or benchmark runner.

## Non-Goals

- Do not build a general-purpose DSL or compiler.
- Do not implement real lowering passes beyond spec generation.
- Do not run performance benchmarks or claim measured performance.
- Do not make event/wait reorder, online softmax formulas, or LSE math freely searchable.
- Do not modify existing Stage 1 artifacts under `artifacts/` except as read-only integration-test inputs.

## Recommended Approach

Use a closed-loop enhancement:

1. Update the skill documentation and output contract.
2. Extend `stage2_parser.py`, `stage2_synthesizer.py`, and `stage2_verifier.py`.
3. Add tests that verify the new artifacts and quality-gate behavior.

This approach is larger than a documentation-only update, but it prevents the new DSL architecture from becoming a paper contract that the tools do not generate or validate.

## Architecture

The existing three-layer pipeline remains:

```text
Stage 1 YAML
  -> stage2_parser.py
      builds EvidenceGraph v0.4
  -> stage2_synthesizer.py
      emits ontology/schema/validators/lowering/shadow + IR/search artifacts
  -> stage2_verifier.py
      scores semantic quality + agent readiness
```

The v0.4 enhancement adds four DSL layers:

| Layer | Purpose | Examples |
|---|---|---|
| `semantic_ir` | Pure operator meaning, shape, dtype, layout intent, side-effect boundaries. No schedule decisions. | interface tensors, shape symbols, online softmax semantics, fixed LSE formulas |
| `kernel_ir` | Schedulable kernel objects and action points. | loops, tiles, buffers, memory scopes, pipeline stages, sparse windows, thread/core mapping |
| `hardware_contract` | Target capabilities and constraints needed for legality and lowering. | UB/L1/workspace capacity, memory spaces, vector/intrinsic placeholders, alignment, profile requirements |
| `execution_feedback` | Agent feedback and replay contracts. | features, metrics, schedule trace fields, tuning record schema, failure categories |

These layers are contracts generated from Stage 1 evidence. They are not executable compiler IR in this stage.

## Output Structure

Existing output paths remain unchanged. New paths are added:

```text
stage2_outputs/
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

  review/
    agent_readiness.md
```

Existing per-module schema files under `schema/modules/` gain optional v0.4 metadata:

```yaml
ir_layer: semantic|kernel|hardware|execution_feedback
schedule_points: []
feature_sources: []
measurement_metrics: []
replay_requirements: []
```

`review/quality_gate.json` remains backward compatible and adds an optional `agent_readiness` object.

## EvidenceGraph Changes

Add node kinds:

| Node kind | Meaning |
|---|---|
| `semantic_entity` | A semantic object such as shape, dtype, layout intent, tensor interface, or fixed formula. |
| `schedule_point` | A possible agent action point such as split, reorder, cache, bind, tensorize, pipeline stage, or tile size choice. |
| `hardware_capability` | A target-sensitive capability or limit required by validation or lowering. |
| `measurement_metric` | A metric that the tuning loop can measure or estimate. |
| `feature_source` | A structured feature source for cost models or similarity retrieval. |
| `tuning_record_field` | A field required to replay or learn from a schedule attempt. |

Add edge labels:

| Edge label | Meaning |
|---|---|
| `field_maps_to_ir` | Connects a DSL field to its IR-layer node. |
| `schedule_point_guarded_by` | Connects a schedule point to a validator. |
| `field_requires_capability` | Connects a field to a hardware capability. |
| `lowering_emits_trace` | Connects a lowering pass to replay/tuning-record fields. |
| `metric_measures_field` | Connects a metric to the fields or schedule points it measures. |
| `feature_derived_from` | Connects a feature source to fields, pipeline nodes, workspace regions, or evidence. |

Graph JSON compatibility is preserved by adding node kinds and edges without changing the existing `nodes` and `edges` top-level structure.

## Synthesizer Behavior

### IR Artifacts

`semantic_ir.yaml` is derived from interface, shape, layout, compute, online softmax, and fixed formula fields. It should separate the operator meaning from schedule/search controls.

`kernel_ir.yaml` is derived from tiling, core mapping, memory, L1 partition/residency, workspace, pipeline, decode, sparse window, and tail policy fields. It should identify schedulable objects and schedule points.

`hardware_contract.yaml` is derived from target, memory hierarchy, L1/UB/workspace validators, alignment fields, and intrinsic-like field names. Unsupported target details are emitted with `needs_evidence: true`.

`execution_feedback.yaml` is derived from tunable knobs, searchable fields, lowering specs, and mandatory metrics. It defines how an agent observes performance, failures, and replay data.

### Search Artifacts

`schedule_space.yaml` lists searchable schedule points, candidates/ranges, source knobs, validators, and forbidden moves.

`feature_schema.yaml` defines structural, memory, mapping, and history features:

- structural: loop extents, ranks, reduction depth, static/dynamic shape markers
- memory: working-set estimates, memory scope, reuse hints, workspace regions
- mapping: core/thread mapping, vector width, tensorize/intrinsic placeholders
- history: similar-shape keys, schedule trace IDs, failure categories

`measurement_schema.yaml` defines metrics such as latency, throughput, bytes moved, occupancy estimate, compile time, correctness result, and failure code. Metrics are schema fields only unless a future stage supplies measured data.

`tuning_record.schema.yaml` defines replay requirements: environment fingerprint, input shape signature, DSL version, schedule trace, validator results, compile result, measurement result, and failure metadata.

### Schema Metadata

For each generated schema field, infer:

- `ir_layer`
- `schedule_points`
- `feature_sources`
- `measurement_metrics`
- `replay_requirements`

Inference should be deterministic and rule-based. Unknown fields should keep `needs_review` behavior and add an explicit `unmapped_ir_layer` issue when the layer cannot be inferred.

## Verifier Behavior

The existing legacy score remains 100 points and keeps the same top-level fields:

- `overall_status`
- `total_score`
- `scores`
- `hard_failures`
- `semantic_issues`
- `coverage`
- `next_actions`

Add optional `agent_readiness`:

```json
{
  "agent_readiness": {
    "status": "pass|warn|fail",
    "score": 0,
    "scores": {
      "ir_layer_mapping": 0,
      "schedule_space_quality": 0,
      "hardware_contract_coverage": 0,
      "feedback_contract_completeness": 0,
      "replayability": 0
    },
    "hard_failures": [],
    "issues": []
  }
}
```

Agent-readiness checks:

- Every searchable field maps to `search/schedule_space.yaml`.
- Every schedule point has at least one validator guard.
- Every hardware-sensitive field links to `hardware_contract.yaml`.
- Every lowering pass declares feature, measurement, or replay needs.
- Every tuning record schema includes environment, shape signature, DSL version, schedule trace, validation result, and outcome fields.
- Shadow DSL examples cover critical fields from the four IR layers.

Agent-readiness hard failures:

- Searchable field with no candidates, range, or enum.
- Schedule point with no validator guard.
- Hardware-sensitive field with no hardware capability contract.
- Event/wait schedule marked searchable without fixed variants and `event_dependency_valid`.
- Online softmax or LSE formula marked searchable.
- Tuning record schema missing schedule trace or outcome fields.

Overall status should fail if the legacy score fails or agent readiness has hard failures.

## Error Handling

- Unknown Stage 1 fields map to `needs_review`; if no IR layer can be inferred, report `unmapped_ir_layer`.
- Unsupported hardware details are emitted as `needs_evidence: true`, not invented.
- Schedule points without validator guards are hard failures.
- Searchable fields without candidates, ranges, or enums remain hard failures.
- Tuning records are schemas only; no measured performance data is fabricated.
- Existing mandatory validators remain enforced for L1 residency, split-KV, workspace, sparse window, and pipeline event dependencies.

## Files To Modify

| File | Change |
|---|---|
| `skills/stage2-dsl-ontology-builder/SKILL.md` | Document v0.4 workflow, new artifacts, and hard constraints. |
| `skills/stage2-dsl-ontology-builder/README.md` | Add quick-start notes for v0.4 outputs. |
| `skills/stage2-dsl-ontology-builder/references/stage2_workflow.md` | Add four-layer IR and feedback bus workflow. |
| `skills/stage2-dsl-ontology-builder/references/output_contract.md` | Add `ir/`, `search/`, schema metadata, and `agent_readiness`. |
| `skills/stage2-dsl-ontology-builder/references/schema_design_rules.md` | Add IR-layer assignment and schedule/search rules. |
| `skills/stage2-dsl-ontology-builder/references/validators_and_lowering.md` | Add schedule guard and replay requirements. |
| `skills/stage2-dsl-ontology-builder/references/quality_gate.md` | Add agent-readiness scoring and hard failures. |
| `skills/stage2-dsl-ontology-builder/agents/openai.yaml` | Add agent role hints for IR/search/feedback contracts. |
| `skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py` | Add v0.4 graph nodes and edges. |
| `skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py` | Generate new `ir/` and `search/` artifacts and schema metadata. |
| `skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py` | Verify agent readiness and write `agent_readiness.md`. |
| `skills/stage2-dsl-ontology-builder/tests/*` | Add fixture, unit, integration, and regression coverage. |

## Test Strategy

Unit tests:

- Parser creates v0.4 node kinds and edges while preserving old graph loading.
- Synthesizer writes all new `ir/` and `search/` files.
- Synthesizer adds v0.4 metadata to generated schema fields.
- Verifier emits `agent_readiness`.
- Verifier catches missing schedule guards, missing hardware contracts, unmapped searchable fields, and invalid searchable formulas.

Integration test:

- Run full pipeline against `artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction`.
- Confirm legacy quality gate still returns `pass|warn|fail`.
- Confirm `agent_readiness` and `review/agent_readiness.md` are present and actionable.

Regression tests:

- `bootstrap_stage2.py` still delegates to parser + synthesizer.
- `check_stage2_quality.py` still delegates to verifier.
- Existing output paths remain present.
- Existing consumers can read `quality_gate.json` without needing the new optional fields.

## Acceptance Criteria

- `python -m pytest skills/stage2-dsl-ontology-builder/tests -v` passes.
- Parser, synthesizer, and verifier can run manually in sequence.
- New docs explain how v0.4 maps the deep report's four-layer IR and feedback-bus recommendation into Stage 2 artifacts.
- `quality_gate.json` remains backward compatible.
- No benchmark or performance claims are emitted without measurement.

## Implementation Order

1. Update tests and fixtures for v0.4 expectations.
2. Extend parser graph model and inference helpers.
3. Extend synthesizer artifact generation.
4. Extend verifier agent-readiness checks.
5. Update skill docs and references.
6. Run unit and integration tests.
7. Update the implementation plan with concrete task checkboxes.
