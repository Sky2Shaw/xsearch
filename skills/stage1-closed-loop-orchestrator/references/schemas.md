# Schemas

All schemas are JSON-compatible YAML. Avoid anchors, aliases, custom tags, and non-scalar map keys.

## run_manifest.yaml

```yaml
run_id: "stage1-loop-20260502T120000Z"
source_root: "/absolute/path/to/source"
loop_root: "/absolute/path/to/source/.xperf_atdsl_loop"
max_rounds: 3
success_score_threshold: 85
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
- `success_score_threshold`: Integer score threshold for terminal success. The loop requires two consecutive scorecards at or above this value.
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
      operator_info_needed:
        - "exact tilingData fields, workspace offsets, loop stage ownership, memory residency, and source evidence for the missing structure"
      acceptance_checks:
        - "Artifact names the kernel entrypoint and source lines."
        - "Critical claims are verified against source."
      evidence_class: "contradicted_or_suspicious"
  score_improvement_targets:
    - dimension: "coverage"
      current_score: 13
      max_score: 25
      score_gap: 12
      related_finding_ids:
        - "BF-001"
      operator_info_needed:
        - "missing operator structures, critical functions, loop stages, memory hierarchy, pipeline stages, workspace layout, masks, and split-KV or merge behavior when present"
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
      objective: "Target only this scoring dimension's missing operator facts before broad regeneration."
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
- `operator_info_needed`
- `acceptance_checks`
- `evidence_class`

`score_improvement_targets` groups safe, structured findings by scoring dimension. It is designed to help the next extractor round focus on the operator facts that are most likely to improve the score. It must not include scorer prose rationale, hidden reasoning, or prior scorer conversation.

## round_summary.yaml

```yaml
round_summary:
  run_id: "stage1-loop-20260502T120000Z"
  round: 1
  status: "continue"
  readiness: "NEEDS_REEXTRACTION"
  total_score: 72
  success_score_threshold: 85
  current_score_meets_threshold: false
  previous_score_meets_threshold: false
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
