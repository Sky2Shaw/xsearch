# Workflow

## Round Chain

Exact chain:

```text
source code -> fresh extractor subagent -> extraction artifacts -> stage1-artifact-scorer/scripts/prepare_review_context.py -> evidence_pack.yaml -> fresh scorer subagent -> scorecard.yaml / blocking_findings.yaml / missing_patterns.yaml / stage2_readiness.yaml -> sanitize_review_findings.py -> reextraction_request.yaml -> next fresh extractor subagent
```

## Round 1

1. Run `init_loop.py` for the source root.
2. Dispatch a fresh extractor subagent.
3. Run `stage1-artifact-scorer/scripts/prepare_review_context.py`.
4. Dispatch a fresh scorer subagent with only allowed inputs.
5. Run `check_stop_conditions.py`.

## Later Rounds

1. Run `sanitize_review_findings.py` on the previous review outputs.
2. Run `prepare_next_round.py`.
3. Dispatch a fresh extractor subagent with only source root, prior artifacts, output location, and `reextraction_request.yaml`.
4. Run `stage1-artifact-scorer/scripts/prepare_review_context.py`.
5. Dispatch a fresh scorer subagent with only allowed inputs.
6. Run `check_stop_conditions.py`.

## Subagent Dispatch Requirements

The user must explicitly authorize isolated subagents before the orchestrator dispatches them. Use `fork_context=false`. Give each subagent only the files and instructions listed in [isolation-policy.md](isolation-policy.md).

## Stop Policy

Stop successfully when gates pass and readiness is acceptable. Stop unsuccessfully on max rounds, stalled improvement, repeated critical blocker, source unavailable, or persistent contradiction.
