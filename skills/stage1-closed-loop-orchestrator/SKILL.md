---
name: stage1-closed-loop-orchestrator
description: Orchestrate isolated Stage 1 extraction and scoring loops for AscendC attention-like operator artifacts. Use when Codex should run extractor and scorer as separate fresh subagents, sanitize review findings into narrow re-extraction requests, and stop when Stage 2 readiness gates and two consecutive score thresholds pass or the loop stops improving.
---

# Stage1 Closed-Loop Orchestrator

## Purpose

This skill coordinates `ascend-operator-structure-extractor` and `stage1-artifact-scorer` in a closed loop. It does not extract Stage 1 knowledge and does not score Stage 1 artifacts. The parent Codex agent dispatches fresh isolated subagents, passes only approved files between roles, and decides whether the loop should continue.

## Required Isolation Rule

Each extractor round must run in a fresh extractor subagent. Each scorer round must run in a fresh scorer subagent. Do not fork the extractor conversation into the scorer. Do not pass scorer reasoning traces into the extractor.

## Allowed Scorer Inputs

- Source root.
- Extraction artifact root.
- `<review_dir>/evidence_pack.yaml`.
- `<review_dir>/source_spot_check_plan.yaml`.
- High-value artifact files and targeted source snippets selected by scorer.

## Allowed Extractor Inputs After Round 1

- Source root.
- Prior extraction artifacts.
- Narrow `reextraction_request.yaml`.
- Extractor skill instructions.

## Forbidden Cross-Context Inputs

- Extractor conversation.
- Extractor self-justification.
- Scorer conversation.
- Scorer hidden or long-form rationale.
- Full `score_report.md` as extractor input.
- Orchestrator opinions about likely fixes.

## Workflow References

- [Workflow](references/workflow.md)
- [Isolation Policy](references/isolation-policy.md)
- [Schemas](references/schemas.md)
- [Prompts](references/prompts.md)

## Defaults

- Default loop root: `<source_root>/.xperf_atdsl_loop/`
- Default round directory: `<loop_root>/round_NNN/`
- Default review directory: `<loop_root>/round_NNN/review/`
- Default max rounds: `3`
- Default terminal readiness: `READY_FOR_STAGE2`
- Default success score threshold: `85`
- Successful termination requires two consecutive scorecards at or above the configured threshold, with gates passing and readiness acceptable.

## Helper Script Entrypoints

These commands are part of the completed orchestrator skill. During implementation, do not invoke a listed script until that script file exists. This is a temporary documentation safety note until later tasks add scripts.

```bash
python3 scripts/init_loop.py --source-root <source_root> --success-score-threshold 85
python3 scripts/prepare_next_round.py --loop-root <loop_root> --from-round 1 --to-round 2
python3 scripts/sanitize_review_findings.py --review-dir <review_dir> --output <reextraction_request.yaml>
python3 scripts/check_stop_conditions.py --loop-root <loop_root> --current-round <round>
python3 skills/stage1-artifact-scorer/scripts/prepare_review_context.py --input <loop_root>/round_001/extraction --output <loop_root>/round_001/review --source-root <source_root>
```

Scripts do not run model judgement. The parent Codex agent dispatches extractor and scorer subagents.

`sanitize_review_findings.py` turns scorer outputs into targeted extraction work. It preserves safe structured fields, infers missing `operator_info_needed` from the weak scoring dimension, and writes `score_improvement_targets` so the next extractor round focuses on the highest-impact operator facts first.

## Final Response

Include these bullets:

- Loop directory.
- Rounds completed.
- Final readiness.
- Final score.
- Gate results.
- Unresolved blockers.
- Final artifact root.
- Final review report path.
- Whether human review is needed.
