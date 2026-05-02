# Workflow

## Round Chain

Exact chain:

```text
source code -> fresh extractor subagent -> <loop_root>/round_NNN/extraction -> stage1-artifact-scorer/scripts/prepare_review_context.py --input <loop_root>/round_NNN/extraction --output <loop_root>/round_NNN/review --source-root <source_root> -> <review_dir>/evidence_pack.yaml -> fresh scorer subagent -> <review_dir>/scorecard.yaml / <review_dir>/blocking_findings.yaml / <review_dir>/missing_patterns.yaml / <review_dir>/stage2_readiness.yaml -> sanitize_review_findings.py -> reextraction_request.yaml -> next fresh extractor subagent
```

Each round's review outputs live in `<loop_root>/round_NNN/review/`.

## Helper Availability

Orchestrator helper commands in this workflow are planned completed-skill entrypoints. During implementation, do not invoke an orchestrator helper script until that script file exists. The scorer context prep command at `skills/stage1-artifact-scorer/scripts/prepare_review_context.py` already exists and can remain a concrete command.

## Round 1

1. Run `init_loop.py` for the source root.
2. Dispatch a fresh extractor subagent.
3. Run `python3 skills/stage1-artifact-scorer/scripts/prepare_review_context.py --input <loop_root>/round_001/extraction --output <loop_root>/round_001/review --source-root <source_root>`.
4. Dispatch a fresh scorer subagent with only allowed inputs, including `<review_dir>/evidence_pack.yaml` and `<review_dir>/source_spot_check_plan.yaml`.
5. Run `check_stop_conditions.py`.

## Later Rounds

1. Run `sanitize_review_findings.py` on the previous review outputs.
2. Run `prepare_next_round.py`.
3. Dispatch a fresh extractor subagent with only source root, prior artifacts, output location, and `reextraction_request.yaml`.
4. Run `python3 skills/stage1-artifact-scorer/scripts/prepare_review_context.py --input <loop_root>/round_NNN/extraction --output <loop_root>/round_NNN/review --source-root <source_root>`.
5. Dispatch a fresh scorer subagent with only allowed inputs, including `<review_dir>/evidence_pack.yaml` and `<review_dir>/source_spot_check_plan.yaml`.
6. Run `check_stop_conditions.py`.

## Subagent Dispatch Requirements

The user must explicitly authorize isolated subagents before the orchestrator dispatches them. The parent Codex agent must use the available subagent dispatch tool with `fork_context=false` when supported. Give each subagent only the files and instructions listed in [isolation-policy.md](isolation-policy.md).

If isolated subagent dispatch is unavailable, stop and ask the user to rerun in an environment with isolated subagents. Do not simulate scorer isolation in the same context.

## Stop Policy

Stop successfully when gates pass and readiness is acceptable. Stop unsuccessfully on max rounds, stalled improvement, repeated critical blocker, source unavailable, or persistent contradiction.
