# Schemas

All schemas are JSON-compatible YAML. Avoid anchors, aliases, custom tags, and non-scalar map keys.

## run_manifest.yaml

```yaml
run_id: "stage1-loop-20260502T120000Z"
source_root: "/absolute/path/to/source"
loop_root: "/absolute/path/to/source/.xperf_atdsl_loop"
max_rounds: 3
acceptable_readiness:
  - "READY_FOR_STAGE2"
copy_mode: "copy"
created_at: "2026-05-02T12:00:00Z"
rounds:
  - round: 1
    round_dir: "/absolute/path/to/source/.xperf_atdsl_loop/round_001"
    extraction_dir: "/absolute/path/to/source/.xperf_atdsl_loop/round_001/extraction"
    review_dir: "/absolute/path/to/source/.xperf_atdsl_loop/round_001/review"
    status: "continue"
```

Fields:

- `run_id`: Stable identifier for this loop run.
- `source_root`: Absolute path to the source under review.
- `loop_root`: Absolute path to the loop directory.
- `max_rounds`: Maximum number of extraction/scoring rounds.
- `acceptable_readiness`: List of readiness values accepted as terminal success, usually containing `READY_FOR_STAGE2`.
- `copy_mode`: Artifact handling mode, such as `copy` or `reference`.
- `created_at`: ISO-8601 timestamp.
- `rounds`: Ordered list of round records with exactly `round`, `round_dir`, `extraction_dir`, `review_dir`, and `status`.

## reextraction_request.yaml

```yaml
reextraction_request:
  run_id: "stage1-loop-20260502T120000Z"
  round: 2
  source_root: "/absolute/path/to/source"
  previous_artifact_root: "/absolute/path/to/source/.xperf_atdsl_loop/round_001/extraction"
  output_artifact_root: "/absolute/path/to/source/.xperf_atdsl_loop/round_002/extraction"
  required_fixes:
    - id: "BF-001"
      severity: "critical"
      type: "missing_artifact"
      dimension: "operator_structure"
      target_files:
        - "cards/operator_structure.yaml"
      target_symbols:
        - "FlashAttentionKernel"
      required_artifacts:
        - "operator_structure_card"
      required_evidence:
        - "source line references for tiling and workspace decisions"
      acceptance_checks:
        - "Artifact names the kernel entrypoint and source lines."
        - "Critical claims are verified against source."
      evidence_class: "contradicted_or_suspicious"
  forbidden_context:
    - "extractor conversation"
    - "extractor self-justification"
    - "scorer conversation"
    - "scorer hidden or long-form rationale"
    - "full score_report.md"
    - "orchestrator opinions about likely fixes"
```

`required_fixes` entries must include:

- `id`
- `severity`
- `type`
- `dimension`
- `target_files`
- `target_symbols`
- `required_artifacts`
- `required_evidence`
- `acceptance_checks`
- `evidence_class`

## round_summary.yaml

```yaml
round_summary:
  run_id: "stage1-loop-20260502T120000Z"
  round: 1
  status: "continue"
  readiness: "NEEDS_REEXTRACTION"
  total_score: 0.72
  gates_passed: false
  blocker_count: 1
  unresolved_blockers:
    - "BF-001"
  next_action: "sanitize_review_findings"
```

Allowed `readiness` values:

- `READY_FOR_STAGE2`
- `READY_WITH_FIXES`
- `NEEDS_REEXTRACTION`
- `NOT_USABLE`

Allowed `status` values:

- `continue`
- `success`
- `needs_human_review`
- `max_rounds_reached`
- `no_improvement`
- `repeated_blocker`
- `source_unavailable`
