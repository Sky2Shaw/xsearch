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
