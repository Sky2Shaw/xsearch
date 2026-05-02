# Prompts

## Extractor Round 1

Use `ascend-operator-structure-extractor` on the provided operator source root and write Stage 1 extraction artifacts to the requested output directory.

Allowed inputs:

- Source root.
- Extractor skill instructions.
- Output location.

Forbidden inputs:

- Scorer conversation.
- Scorer hidden or long-form rationale.
- Scorer reasoning traces.
- Full `score_report.md`.
- Orchestrator opinions about likely fixes.

Do not score the artifacts. Do not infer review expectations from anything outside the allowed inputs.

## Extractor Re-Extraction

Use `ascend-operator-structure-extractor` to update or regenerate only the artifacts requested by `reextraction_request.yaml`.

Allowed inputs:

- Source root.
- Prior extraction artifacts.
- Narrow `reextraction_request.yaml`.
- Extractor skill instructions.
- Output location.

Forbidden inputs:

- Extractor conversation from prior rounds.
- Extractor self-justification.
- Scorer conversation.
- Scorer hidden or long-form rationale.
- Scorer reasoning traces.
- Full `score_report.md` as extractor input.
- Orchestrator opinions about likely fixes.

Honor the request exactly. Use source evidence for every critical correction.

Use `score_improvement_targets` as the work plan for the round. Start with the largest score gaps and blocking findings. Extract the named operator facts, source evidence, target symbols, required artifacts, and acceptance checks. Avoid broad regeneration when a targeted artifact update can satisfy the request.

## Scorer

Use `stage1-artifact-scorer` to review Stage 1 extraction artifacts. Treat artifacts as claims, not facts. Verify critical claims against source code before accepting them.

Allowed inputs:

- Source root.
- Extraction artifact root.
- `<review_dir>/evidence_pack.yaml`.
- `<review_dir>/source_spot_check_plan.yaml`.
- High-value artifact files and targeted source snippets selected by scorer.

Forbidden inputs:

- Extractor conversation.
- Extractor self-justification.
- Extractor hidden or long-form rationale.
- Orchestrator opinions about artifact quality.
- Prior scorer hidden reasoning traces.
- prior scorer conversation.
- Prior score reports.
- Prior scorecards.
- Prior round summaries.
- Any hidden rationale.

Produce structured scorer outputs in `<review_dir>/`, including `scorecard.yaml`, `blocking_findings.yaml`, `missing_patterns.yaml`, and `stage2_readiness.yaml`.

Each blocking finding or missing pattern should be actionable for a later isolated extractor round. Include structured fields such as `dimension`, `severity`, `target_files`, `target_symbols`, `required_artifacts`, `required_evidence`, `operator_info_needed`, and `acceptance_checks`. These fields should name missing or incorrect operator facts, not broad advice.

Only the parent orchestrator compares prior scorecards and prior round summaries outside scorer context.
