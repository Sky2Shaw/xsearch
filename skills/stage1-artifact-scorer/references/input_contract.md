# Stage-1 Artifact Input Contract

Recommended directory:

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

## Supported Extraction Layout

The scorer accepts the original generic `stage1_outputs/` layout and the extractor-native `.xperf_atdsl_extraction/` layout:

```text
.xperf_atdsl_extraction/
  annotations/functions/index/
  annotations/functions/brief/
  annotations/functions/deep/
  annotations/files/
  reports/function_index.yaml
  reports/function_importance.yaml
  reports/critical_path_annotations.yaml
  cards/optimization_cards.yaml
  dsl/suggested_dsl_sections.yaml
  dsl/schema_gaps.yaml
  knobs/tunable_knobs.yaml
  constraints/constraints.yaml
  risks/risks.yaml
```

## AI Review Context Outputs

```text
stage1_review/
  evidence_pack.yaml
  inventory.yaml
  cross_reference.yaml
  source_spot_check_plan.yaml
```

If `evidence_pack.yaml` contains `blocking_findings`, those are deterministic precheck finding ids from context preparation, not final AI review findings. Final review findings belong in `stage1_review/blocking_findings.yaml`.

## Final AI Review Outputs

```text
stage1_review/
  score_report.md
  scorecard.yaml
  blocking_findings.yaml
  missing_patterns.yaml
  recommended_fixes.md
  stage2_readiness.yaml
```

## Required artifact classes

1. Function annotations
2. Optimization cards
3. Tunable knobs
4. Hard constraints
5. Risks/failure modes
6. Source evidence

## Helpful auxiliary classes

1. Dataflow graphs
2. Pipeline graphs
3. Memory lifetime tables
4. Workspace layout tables

## Minimal function annotation

```yaml
function_annotation:
  file:
  function:
  role:
  inputs: []
  outputs: []
  dataflow: []
  memory_behavior: []
  pipeline_stage:
  tunable_knobs: []
  constraints: []
  risks: []
  possible_dsl_section: []
  source_evidence: []
```

## Minimal optimization card

```yaml
optimization_card:
  id:
  canonical_name:
  aliases: []
  pattern: []
  intent: []
  applies_to: []
  preconditions: []
  tunable_knobs: []
  constraints: []
  risks: []
  possible_dsl_fields: []
  lowering_hint: []
  source_evidence: []
```
