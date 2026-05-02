# Stage1 Closed-Loop Orchestrator Design

Date: 2026-05-02

## Goal

Create a Codex skill named `stage1-closed-loop-orchestrator` that automates the Stage 1 extraction and review loop for AscendC attention-like operators while preserving strict reviewer independence.

The orchestrator must:

1. Run extraction with `ascend-operator-structure-extractor`.
2. Run review with `stage1-artifact-scorer`.
3. Convert review findings into a narrow re-extraction request.
4. Repeat until gates pass, the loop stops improving, or the max round count is reached.
5. Prevent extractor context from polluting scorer judgement, and prevent scorer reasoning from teaching the extractor how to game the score.

The core principle is:

```text
extractor produces artifacts
scorer reviews artifacts and source evidence
orchestrator moves only minimal structured facts between them
```

## Non-Goals

1. Do not merge extractor and scorer into one large skill.
2. Do not let scripts assign final AI review scores.
3. Do not build a daemon or fully unattended external service in the first version.
4. Do not optimize or patch AscendC kernels.
5. Do not use scorer Markdown reports as control-flow input; use machine-readable YAML only.

## Codex Compatibility

The design is implementable inside Codex as a skill-driven workflow.

Model judgement steps still require Codex agents:

- The extractor step is a fresh extractor subagent.
- The scorer step is a fresh scorer subagent.
- The orchestrator is the parent agent that coordinates files, rounds, and stop conditions.

Helper scripts may create directories, prepare manifests, sanitize findings, and compare scorecards. They must not pretend to call Codex skills or perform final semantic review on their own.

The isolation guarantee is context isolation inside the Codex workflow: the scorer is not given extractor conversation or self-justification, and the extractor is not given scorer reasoning traces. It is not a claim about model-weight-level isolation.

Because Codex subagents require explicit user intent, the orchestrator skill should document an invocation such as:

```text
Use $stage1-closed-loop-orchestrator with isolated subagents on <operator_dir>.
```

That invocation gives the parent Codex agent permission to spawn isolated extractor and scorer subagents for the loop.

## Recommended Approach

Use a third skill as an orchestration layer:

```text
skills/stage1-closed-loop-orchestrator/
  SKILL.md
  references/
    workflow.md
    isolation-policy.md
    schemas.md
    prompts.md
  scripts/
    init_loop.py
    prepare_next_round.py
    sanitize_review_findings.py
    check_stop_conditions.py
  agents/
    openai.yaml
```

This is better than merging the existing skills because the extractor and scorer keep separate purposes, separate prompts, separate contexts, and separate artifact contracts.

## Runtime Layout

For each analyzed operator, the orchestrator writes loop state under:

```text
.xperf_atdsl_loop/
  run_manifest.yaml
  round_001/
    extraction/
    review/
    reextraction_request.yaml
    round_summary.yaml
  round_002/
    extraction/
    review/
    reextraction_request.yaml
    round_summary.yaml
  final_report.md
  final_readiness.yaml
```

The existing extractor-native `.xperf_atdsl_extraction/` layout remains valid. The loop may either copy each round's artifacts into `round_N/extraction/` or point each round to a stable extraction directory through `run_manifest.yaml`. Copying is safer for auditability; stable in-place output is faster but makes diffs harder to inspect.

The recommended default is copy-per-round.

## Roles

### Orchestrator

The orchestrator coordinates the loop. It may:

- create round directories;
- dispatch extractor and scorer subagents;
- run deterministic scripts;
- prepare `stage1_review/evidence_pack.yaml`;
- sanitize scorer findings into `reextraction_request.yaml`;
- compare scorecards between rounds;
- decide when to stop.

It must not:

- create extraction content itself;
- assign final review scores;
- rewrite scorer findings to make results look better;
- pass full extractor conversation to scorer;
- pass full scorer reasoning to extractor.

### Extractor Subagent

Each extraction round uses a fresh extractor subagent with no inherited conversation context.

Allowed inputs:

- source root;
- current extraction artifact root, if continuing from a prior round;
- `reextraction_request.yaml`;
- `ascend-operator-structure-extractor` skill instructions and relevant references.

Forbidden inputs:

- scorer subagent conversation;
- full `score_report.md`;
- scorer hidden or long-form rationale;
- prior extractor conversation except through artifacts already written to disk.

The extractor must produce or update Stage 1 artifacts, not review itself.

### Scorer Subagent

Each review round uses a fresh scorer subagent with no inherited extractor context.

Allowed inputs:

- source root;
- extraction artifact root;
- `stage1_review/evidence_pack.yaml`;
- `stage1_review/source_spot_check_plan.yaml`;
- high-value artifact files referenced by the evidence pack;
- targeted source snippets selected by the scorer.

Forbidden inputs:

- extractor subagent conversation;
- extractor self-justification;
- orchestrator opinions about likely fixes;
- prior full scorer report, except compact score deltas if needed for comparison.

The scorer must treat artifacts as claims, not truth. Source-backed checks are required for high accuracy scores.

## Workflow

Each round follows this chain:

```text
source code
  -> fresh extractor subagent
  -> extraction artifacts
  -> prepare_review_context.py
  -> evidence_pack.yaml
  -> fresh scorer subagent
  -> scorecard.yaml / blocking_findings.yaml / recommended_fixes.md
  -> sanitizer script
  -> reextraction_request.yaml
  -> next fresh extractor subagent
```

### Round 1

1. Initialize `.xperf_atdsl_loop/`.
2. Run extractor from source code into `round_001/extraction/`.
3. Run `stage1-artifact-scorer/scripts/prepare_review_context.py`.
4. Dispatch scorer with only source, artifacts, evidence pack, and scorer instructions.
5. Write scorer outputs under `round_001/review/`.
6. Check stop conditions.

### Later Rounds

1. Sanitize scorer findings into `round_N/reextraction_request.yaml`.
2. Dispatch a fresh extractor with source, prior artifacts, and re-extraction request.
3. Produce updated artifacts under the next round.
4. Dispatch a fresh scorer.
5. Compare machine-readable gates, scores, and blocker counts.

## Sanitized Re-Extraction Request

The orchestrator must not feed the full review report back to the extractor. It should generate a narrow YAML request:

```yaml
reextraction_request:
  run_id: string
  round: 2
  source_root: string
  previous_artifact_root: string
  output_artifact_root: string
  required_fixes:
    - id: missing_flash_decode_merge
      severity: blocking
      type: missing_critical_coverage
      target_files:
        - path/to/source.cpp
      target_symbols:
        - FlashDecodeMerge
      required_artifacts:
        - reports/critical_path_annotations.yaml
        - annotations/functions/deep/
        - cards/optimization_cards.yaml
      required_evidence:
        - file
        - function
        - line_range
        - observed_behavior
      acceptance_checks:
        - critical_path_deep_coverage includes flash_decode.merge
        - source evidence cites merge behavior
  forbidden_context:
    - extractor_conversation
    - scorer_reasoning_trace
    - full_score_report
```

The request should preserve what is missing and how it will be accepted, but omit scorer prose, score weights, and reviewer deliberation.

## Scorer Accuracy Rules

The scorer must classify important claims with one of:

```text
verified_against_source
supported_by_artifacts_only
not_verifiable
contradicted_or_suspicious
```

High `accuracy` scores require `verified_against_source` evidence. If an artifact merely claims a behavior, it may support coverage or traceability, but not strong source accuracy.

Every blocking finding should include:

```yaml
id: string
severity: blocking | major | minor
dimension: coverage | accuracy | traceability | dsl_convertibility | risks_constraints | dedup
evidence_class: verified_against_source | supported_by_artifacts_only | not_verifiable | contradicted_or_suspicious
source_or_artifact_ref:
  - path: string
    function: string | null
    line_range: object | null
summary: string
required_fix: string
```

## Stop Conditions

The loop stops successfully when:

- all configured gates pass; and
- either readiness is `READY_FOR_STAGE2`, or the user explicitly configured `READY_WITH_FIXES` as an acceptable terminal state.

Default gates:

```text
coverage
accuracy
dsl_convertibility
important_card_evidence_coverage
critical_path_deep_coverage
template_identity_coverage
```

The loop stops without success when any of these occur:

1. The max round count is reached. Default: `3`.
2. Two consecutive rounds show no score improvement and no blocker reduction.
3. The same critical gap repeats after a re-extraction request.
4. A key artifact is `contradicted_or_suspicious` twice without new source evidence.
5. Source root or critical source files are unavailable, making source-aware accuracy impossible.

When stopped without success, write `final_readiness.yaml` with `NEEDS_HUMAN_REVIEW`, `NEEDS_REEXTRACTION`, or `NOT_USABLE` according to the latest scorer output.

## Script Boundaries

### `init_loop.py`

Creates `.xperf_atdsl_loop/`, writes `run_manifest.yaml`, and initializes round 1 directories.

### `prepare_next_round.py`

Copies or links prior extraction artifacts into the next round and prepares expected output paths.

### `sanitize_review_findings.py`

Reads:

- `scorecard.yaml`
- `blocking_findings.yaml`
- `missing_patterns.yaml`
- selected structured fields from `stage2_readiness.yaml`

Writes:

- `reextraction_request.yaml`

It must ignore free-form Markdown except as a human-readable attachment. Control logic should depend on YAML.

### `check_stop_conditions.py`

Reads current and previous `scorecard.yaml`, blocker counts, gate results, and round metadata. Writes `round_summary.yaml` and returns a status:

```text
continue
success
needs_human_review
max_rounds_reached
no_improvement
source_unavailable
```

## Skill Entrypoint

`SKILL.md` should stay short. It should state:

- when to use the orchestrator;
- that isolated subagents are mandatory for extraction and scoring;
- that the skill does not merge extractor and scorer roles;
- the allowed and forbidden context flow;
- the default max round count;
- the expected final response.

The final response should report:

- loop directory;
- rounds completed;
- final readiness;
- final score;
- gate results;
- unresolved blockers;
- final artifact root;
- final review report path;
- whether human review is needed.

## Testing Strategy

Focused tests should cover deterministic scripts:

1. `sanitize_review_findings.py` converts structured findings into a narrow re-extraction request.
2. Sanitizer does not include full scorer Markdown or reviewer rationale.
3. `check_stop_conditions.py` detects success, no improvement, repeated blocker, and max-round states.
4. `init_loop.py` creates predictable directories and manifests.
5. The orchestrator docs forbid passing extractor context into scorer and scorer reasoning into extractor.

Manual verification should run one small loop on sample artifacts to confirm that files land in the expected locations and the scorer receives only the allowed evidence inputs.

## Risks

### Subagent Permission Ambiguity

Codex only allows subagent spawning when the user explicitly requests subagents, delegation, or parallel agent work. The skill must make this invocation requirement explicit.

### Scorer Drift

If scorer reports become too narrative, the sanitizer may accidentally carry reviewer framing back into extraction. The sanitizer should prefer structured fields and drop prose by default.

### Extractor Overfitting

If the extractor receives score weights or full scorer rationale, it may write artifacts that look score-friendly without improving evidence. The re-extraction request must contain concrete missing evidence and acceptance checks, not scoring strategy.

### Source Availability

When source files are missing or incomplete, the scorer must lower accuracy confidence and the orchestrator must not mark the loop as truly ready.

## Acceptance Criteria

The design is implemented correctly when:

1. A user can invoke one orchestrator skill for a bounded Stage 1 extraction-review loop.
2. Extractor and scorer run in fresh, isolated subagent contexts.
3. Scorer never receives extractor conversation or self-justification.
4. Extractor never receives full scorer reports or scorer reasoning traces.
5. The loop uses machine-readable YAML for control decisions.
6. Stop conditions prevent endless or self-reinforcing loops.
7. Final output clearly distinguishes ready, ready with fixes, needs re-extraction, and needs human review.
