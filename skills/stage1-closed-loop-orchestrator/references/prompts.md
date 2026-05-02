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

## Scorer

Use `stage1-artifact-scorer` to review Stage 1 extraction artifacts. Treat artifacts as claims, not facts. Verify critical claims against source code before accepting them.

Allowed inputs:

- Source root.
- Extraction artifact root.
- `stage1_review/evidence_pack.yaml`.
- `stage1_review/source_spot_check_plan.yaml`.
- High-value artifact files and targeted source snippets selected by scorer.

Forbidden inputs:

- Extractor conversation.
- Extractor self-justification.
- Extractor hidden or long-form rationale.
- Orchestrator opinions about artifact quality.
- Prior scorer hidden reasoning traces.
- Prior scorer conversation unless explicitly part of structured review artifacts.

Produce structured scorer outputs, including `scorecard.yaml`, `blocking_findings.yaml`, `missing_patterns.yaml`, and `stage2_readiness.yaml`.
