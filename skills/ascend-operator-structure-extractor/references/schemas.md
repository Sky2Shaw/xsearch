# Schemas

- [function_index](#function_index)
- [function_brief](#function_brief)
- [function_annotation](#function_annotation)
- [file_analysis](#file_analysis)
- [analysis_result](#analysis_result)
- [evolution_result](#evolution_result)

These schemas define expected YAML artifact shapes. Use `unknown` for missing evidence. Prefer lists of objects when multiple source-backed facts must carry separate evidence, confidence, or location data.

## function_index

```yaml
function_name: string
qualified_name: string
canonical_name: string
owner: string | null
owner_qualified: string | null
owner_template_args:
  - string
template_params:
  - string
variant: gqa | mla | flash_decode | nonquant | unknown
stage: mm1 | mm2 | vec1 | vec2 | softmax | flash_decode | workspace | tiling | metadata | unknown
file: string
line_range:
  start: integer
  end: integer
calls:
  - string
called_by:
  - string
rough_role: string
importance_score: number
importance_reasons:
  - string
extraction_level: index | brief | deep
```

## function_brief

```yaml
function_name: string
qualified_name: string
canonical_name: string
owner: string | null
owner_qualified: string | null
owner_template_args:
  - string
template_params:
  - string
variant: gqa | mla | flash_decode | nonquant | unknown
stage: mm1 | mm2 | vec1 | vec2 | softmax | flash_decode | workspace | tiling | metadata | unknown
file: string
line_range:
  start: integer
  end: integer
role: string
touches:
  - string
calls:
  - string
called_by:
  - string
possible_risks:
  - string
related_dsl_sections:
  - string
need_deep_extract:
  value: boolean
  reason: string
confidence: high | medium | low
```

## function_annotation

```yaml
function_name: string
qualified_name: string
canonical_name: string
owner: string | null
owner_qualified: string | null
owner_template_args:
  - string
template_params:
  - string
variant: gqa | mla | flash_decode | nonquant | unknown
stage: mm1 | mm2 | vec1 | vec2 | softmax | flash_decode | workspace | tiling | metadata | unknown
file: string
line_range:
  start: integer
  end: integer
role: string
confidence: high | medium | low
code_behavior:
  summary: string
  key_steps:
    - string
dataflow:
  inputs:
    - string
  outputs:
    - string
  gm:
    reads:
      - string
    writes:
      - string
  ub:
    reads:
      - string
    writes:
      - string
  l1:
    reads:
      - string
    writes:
      - string
  l0:
    l0a:
      - string
    l0b:
      - string
    l0c:
      - string
control_flow:
  loops:
    - string
  branches:
    - string
pipeline:
  stages:
    - string
  sync:
    - string
memory_behavior:
  buffers:
    - string
  l1_residency:
    - string
  l1_partition:
    - string
tiling_and_shape:
  fields:
    - string
  shape_assumptions:
    - string
workspace:
  layout:
    - string
  offsets:
    - string
optimization_intent:
  - string
tunable_or_structural_fields:
  - name: string
    role: string
    evidence: string
constraints:
  - string
risks_if_changed:
  - string
possible_dsl_sections:
  - string
suggested_dsl_fields:
  - path: string
    meaning: string
    evidence: string
    confidence: high | medium | low
lowering_hints:
  - string
open_questions:
  - string
```

## file_analysis

```yaml
file: string
file_role: string
important_functions:
  - qualified_name: string
    role: string
    reason: string
file_level_dataflow:
  - string
file_level_pipeline:
  - string
memory_strategy:
  - string
l1_strategy:
  - string
decode_strategy:
  - string
optimization_cards:
  - id: string
    title: string
    evidence:
      - string
    criteria_met:
      - string
    confidence: high | medium | low
tunable_knobs:
  - name: string
    role: string
    evidence: string
constraints:
  - string
risks:
  - string
suggested_dsl_sections:
  - name: string
    fields:
      - string
    evidence: string
```

## analysis_result

```yaml
metadata:
  operator_family: string
  target_root: string
  output_root: string
  generated_at: string
coverage:
  files_total: integer
  functions_total: integer
  functions_indexed: integer
  functions_brief: integer
  functions_deep: integer
  known_gaps:
    - string
operator_summary:
  role: string
  major_paths:
    - string
  confidence: high | medium | low
files_analyzed:
  - file: string
    file_role: string
    artifact: string
optimization_cards:
  - id: string
    title: string
    pattern: string
    evidence:
      - string
    confidence: high | medium | low
tunable_knobs:
  - name: string
    scope: string
    evidence: string
constraints:
  - id: string
    description: string
    evidence: string
risks:
  - id: string
    description: string
    evidence: string
suggested_dsl_sections:
  - name: string
    purpose: string
    fields:
      - path: string
        meaning: string
        evidence: string
        confidence: high | medium | low
lowering_hints:
  - hint: string
    evidence: string
    confidence: high | medium | low
open_questions:
  - question: string
    missing_evidence: string
```

## evolution_result

```yaml
new_patterns:
  - id: string
    operator_family: string
    code_evidence:
      - string
    dsl_field_path: string
    optimization_intent: string
    confidence: high | medium | low
updated_patterns:
  - id: string
    change: string
    reason: string
    confidence: high | medium | low
checklist_updates:
  - section: string
    item: string
    evidence: string
negative_lessons:
  - id: string
    lesson: string
    evidence: string
    avoid_when: string
schema_gaps:
  - path: string
    gap: string
    evidence: string
skill_patch_proposal:
  - file: string
    proposed_change: string
    reason: string
    confidence: high | medium | low
conflicts:
  - conflict: boolean
    conflict_reason: string
    related_ids:
      - string
    confidence: high | medium | low
```
