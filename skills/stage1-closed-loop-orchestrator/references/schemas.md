# Schemas

All schemas are JSON-compatible YAML. Avoid anchors, aliases, custom tags, and non-scalar map keys.

## run_manifest.yaml

```yaml
run_id: "stage1-loop-20260502T120000Z"
source_root: "/absolute/path/to/source"
loop_root: "/absolute/path/to/source/.xperf_atdsl_loop"
max_rounds: 3
acceptable_readiness: "READY_FOR_STAGE2"
copy_mode: "copy"
created_at: "2026-05-02T12:00:00Z"
rounds:
  - round: 1
    status: "continue"
    artifact_root: "/absolute/path/to/source/.xperf_atdsl_loop/rounds/1/artifacts"
    review_dir: "/absolute/path/to/source/.xperf_atdsl_loop/rounds/1/stage1_review"
    round_summary: "/absolute/path/to/source/.xperf_atdsl_loop/rounds/1/round_summary.yaml"
```

Fields:

- `run_id`: Stable identifier for this loop run.
- `source_root`: Absolute path to the source under review.
- `loop_root`: Absolute path to the loop directory.
- `max_rounds`: Maximum number of extraction/scoring rounds.
- `acceptable_readiness`: Terminal readiness threshold, usually `READY_FOR_STAGE2`.
- `copy_mode`: Artifact handling mode, such as `copy` or `reference`.
- `created_at`: ISO-8601 timestamp.
- `rounds`: Ordered list of round records.

## reextraction_request.yaml

```yaml
request_id: "round-2-reextraction"
source_round: 1
target_round: 2
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
round: 1
status: "continue"
readiness: "NOT_READY_FOR_STAGE2"
score: 0.72
gate_results:
  source_coverage: "pass"
  evidence_quality: "fail"
  contradiction_check: "pass"
unresolved_blockers:
  - "BF-001"
artifact_root: "/absolute/path/to/source/.xperf_atdsl_loop/rounds/1/artifacts"
review_report_path: "/absolute/path/to/source/.xperf_atdsl_loop/rounds/1/stage1_review/score_report.md"
human_review_needed: false
created_at: "2026-05-02T12:30:00Z"
```

Allowed `status` values:

- `continue`
- `success`
- `needs_human_review`
- `max_rounds_reached`
- `no_improvement`
- `repeated_blocker`
- `source_unavailable`
