# Stage-1 Scoring Rubric

## Total score: 100

| Dimension | Weight | Passing signal | Failing signal |
|---|---:|---|---|
| Coverage | 25 | Captures all major FA/FlashDecode structures | Misses L1, workspace, pipeline, split-KV, or event sync |
| Accuracy | 25 | Matches code facts; no invented behavior | Wrong memory space, loop order, function role, or reuse scope |
| Traceability | 15 | Important claims cite file/function/behavior | Cards have no source evidence |
| DSL-convertibility | 20 | Can produce module/field/enum/knob/validator/lowering hint | Mostly prose summaries |
| Risk & constraints | 10 | Captures hard constraints and forbidden transforms | Only says what to optimize, not what to protect |
| Dedup & canonicalization | 5 | Stable canonical names and aliases | Repeated patterns under many names |

## Gate conditions

- Coverage must be >= 18/25.
- Accuracy must be >= 20/25.
- DSL-convertibility must be >= 15/20.
- Important optimization cards must have >= 90% evidence coverage.
- If human spot checks are provided, accuracy must be >= 85%.
- Critical path deep coverage must be 100% for declared critical stages.
- Template identity coverage must be 100% for critical functions, including `canonical_name`, `owner`, `owner_qualified`, `owner_template_args`, `template_params`, `variant`, and `stage`.
- GQA/MLA MM2 paths must not be collapsed into generic MM2.
- MLA nUpdate and FlashDecode merge must be covered when present in the operator.
- Script-produced accuracy is not final accuracy; final accuracy comes from AI review with source spot checks.

## Readiness mapping

- 85-100: READY_FOR_STAGE2
- 70-84: READY_WITH_FIXES
- 50-69: NEEDS_REEXTRACTION
- 0-49: NOT_USABLE
