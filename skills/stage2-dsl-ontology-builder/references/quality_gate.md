# Stage 2 Quality Gate

## Scoring

Use 100 points:

| Dimension | Weight |
|---|---:|
| Card-to-module coverage | 20 |
| Field design completeness | 20 |
| Searchable knob quality | 15 |
| Validator completeness | 20 |
| Lowering pass clarity | 10 |
| Shadow DSL coverage | 15 |

## Pass thresholds

- `>= 85`: ready to implement validators or lowering MVP.
- `70-84`: usable but must fix listed issues first.
- `< 70`: do not proceed; revisit Stage 1 or redo schema design.

## Hard failures

Fail or warn strongly if:

- A DSL module has no source card.
- A high-risk field has no validator.
- A searchable field has no candidates or range.
- L1 residency has no L1 capacity validator.
- L1 residency across G has no loop-order validator.
- split-KV has no partial workspace fields.
- split-KV has no LSE merge validator.
- workspace fields have no no-alias validator.
- event schedules are searchable without a fixed variant set.
- No mature kernel can be represented as shadow DSL.

## Required review files

- `schema_review.md`: narrative review.
- `coverage_matrix.md`: card/module/field/validator matrix.
- `missing_fields.md`: gaps and evidence needs.
- `quality_gate.json`: machine-readable result.
