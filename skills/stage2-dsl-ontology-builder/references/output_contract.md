# Stage 2 Output Contract

## Required directory

```text
stage2_outputs/
  ontology/
  schema/modules/
  validators_spec/
  lowering_spec/
  examples/
  review/
```

## `ontology/canonical_optimizations.yaml`

Each item must include:

```yaml
- id:
  aliases: []
  intent: []
  applies_to: []
  preconditions: []
  risks: []
  required_dsl_modules: []
  suggested_fields: []
  searchable_knobs: []
  validators: []
  lowering_passes: []
  source_evidence: []
```

## `ontology/modules.yaml`

Each module must include:

```yaml
- name:
  responsibility:
  profile_scope: []
  source_cards: []
  core_fields: []
  searchable_fields: []
  hard_validators: []
  lowering_passes: []
```

## Per-module schema

Each field should include:

```yaml
field_name:
  type:
  default:
  enum: []
  candidates: []
  searchable: false
  editable_policy: fixed
  source_cards: []
  source_evidence: []
  related_validators: []
  lowering_consumers: []
```

Use `needs_evidence: true` for useful fields that are not yet strongly supported by Stage 1 evidence.

## Validator spec

Each validator file must include:

```yaml
name:
module:
severity: hard
inputs: []
expr:
error_message:
related_risks: []
source_cards: []
source_evidence: []
```

## Lowering pass spec

Each lowering pass file must include:

```yaml
name:
consumes: []
emits: []
patch_points: []
pre_validators: []
post_validators: []
editable_policy:
source_cards: []
```

## Quality gate

`review/quality_gate.json` must contain:

```json
{
  "overall_status": "pass|warn|fail",
  "scores": {
    "card_to_module_coverage": 0,
    "field_evidence": 0,
    "searchable_knob_quality": 0,
    "validator_coverage": 0,
    "lowering_spec_clarity": 0,
    "shadow_dsl_coverage": 0
  },
  "hard_failures": [],
  "next_actions": []
}
```

## Extended quality_gate.json (v0.3)

The semantic verifier extends `quality_gate.json` with these additional fields:

```json
{
  "semantic_issues": [
    {
      "severity": "error|warning",
      "category": "evidence|schema|knob|validator|lowering|shadow",
      "message": "human-readable description",
      "remediation": "suggested fix"
    }
  ],
  "coverage": {
    "shadow_dsl": {
      "variant_name": {"covered": 8, "total": 12, "pct": 66.7}
    }
  },
  "next_actions": ["ordered list of fixes"]
}
```

All new fields are optional for backward compatibility. Consumers that only read `overall_status` and `scores` continue to work unchanged.

## Stage 2 v0.4 agent-ready outputs

Additional directories:

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
```

Per-field schema entries may include:

```yaml
ir_layer: semantic|kernel|hardware|execution_feedback|needs_review
schedule_points: []
feature_sources: []
measurement_metrics: []
replay_requirements: []
```

`quality_gate.json` may include:

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
