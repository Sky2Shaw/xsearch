# Isolation Policy

## Purpose

The orchestrator enforces Codex workflow context isolation between extractor and scorer roles. This is context isolation for the agent workflow, not model-weight-level isolation.

## Extractor Inputs

Round 1 extractor inputs:

- Source root.
- Extractor skill instructions.
- Output location.

Allowed extractor inputs after round 1:

- Source root.
- Prior extraction artifacts.
- Narrow `reextraction_request.yaml`.
- Extractor skill instructions.

Forbidden extractor inputs:

- Extractor conversation.
- Extractor self-justification.
- Scorer conversation.
- Scorer hidden or long-form rationale.
- Full `score_report.md` as extractor input.
- Orchestrator opinions about likely fixes.

## Scorer Inputs

Allowed scorer inputs:

- Source root.
- Extraction artifact root.
- `stage1_review/evidence_pack.yaml`.
- `stage1_review/source_spot_check_plan.yaml`.
- High-value artifact files and targeted source snippets selected by scorer.

Forbidden scorer inputs:

- Extractor conversation.
- Extractor self-justification.
- Orchestrator opinions about artifact quality.
- Prior scorer hidden reasoning traces.
- Extractor hidden or long-form rationale.

## Sanitizer Rules

The sanitizer may read:

- `scorecard.yaml`.
- `blocking_findings.yaml`.
- `missing_patterns.yaml`.
- `stage2_readiness.yaml`.

The sanitizer must emit narrow, structured fix requests. It must not copy Markdown rationale, hidden reasoning, or prose recommendations. It must not include scorer conversation, scorer reasoning traces, or broad advice for the extractor.

## Evidence Classes

- `verified_against_source`: Directly checked against source code.
- `supported_by_artifacts_only`: Supported by extraction artifacts but not independently source-verified.
- `not_verifiable`: Could not be verified from available source or artifacts.
- `contradicted_or_suspicious`: Contradicted by source or suspicious enough to require re-extraction.

High accuracy requires `verified_against_source` evidence for critical claims.
