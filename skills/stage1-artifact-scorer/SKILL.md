---
name: stage1-artifact-scorer
description: Score Stage-1 extraction artifacts for an AscendC FlashAttention/FlashDecode tuning DSL project. Use when reviewing function annotations, optimization cards, tunable knobs, constraints, risks, source evidence, dataflow/pipeline graphs, memory lifetime, or workspace layout before Stage-2 DSL schema design.
---

# Stage-1 Artifact Scorer Skill

## Purpose

Use this skill to perform an AI review of Stage-1 extraction artifacts before Stage-2 DSL ontology/schema design for AscendC FlashAttention, Sparse FlashAttention, FlashDecode, GQA, MQA, MLA, split-KV decode, and related kernels.

The skill is review-oriented. The helper script prepares deterministic evidence. The AI reviewer assigns the final quality judgement by inspecting the evidence pack, high-value artifacts, and targeted source snippets.

The review decides whether artifacts are:

1. Complete enough to cover mature AscendC attention-kernel optimization structures.
2. Accurate against source code facts, or clearly marked as not verified.
3. Traceable to file/function/code behavior.
4. Structured enough to become DSL modules, fields, enums, constraints, validators, and lowering hints.
5. Explicit about risks, hard constraints, forbidden transforms, and failure modes.
6. Deduplicated enough to avoid fragmenting the Stage-2 schema.

## When to use

Use this skill when the user asks to:

- score Stage-1 extraction output;
- review `function_annotation`, `optimization_card`, `tunable_knobs`, `constraints`, `risks`, or `source_evidence`;
- decide whether Stage-1 artifacts can enter Stage-2 DSL design;
- generate a Stage-1 review report;
- compare extraction artifacts against mature AscendC FlashAttention / FlashDecode source code;
- find missing optimization patterns before DSL schema design.

Do not use this skill to optimize kernels directly. Do not generate AscendC patches unless the user explicitly asks for lowering or implementation.

## Expected inputs

Look for one or more of these directories/files. If names differ, infer equivalents by content.

```text
stage1_outputs/
  annotations/              # function-level annotations
  cards/                    # optimization cards
  knobs/                    # tunable knobs
  constraints/              # hard constraints
  risks/                    # risk/failure-mode records
  evidence/                 # source evidence links
  auxiliary/
    dataflow_graphs.*
    pipeline_graphs.*
    memory_lifetime.*
    workspace_layout.*
```

Also inspect relevant source files if available, especially AscendC kernel files, host tiling files, tilingData definitions, tests, and benchmark notes.

## AI Review Workflow

### 0. Prepare review context

Run:

```bash
python3 scripts/prepare_review_context.py \
  --input <stage1_output_or_.xperf_atdsl_extraction> \
  --output <stage1_output_or_.xperf_atdsl_extraction>/stage1_review
```

If the source operator directory is not obvious, pass:

```bash
  --source-root <operator_source_dir>
```

The script writes:

```text
stage1_review/evidence_pack.yaml
stage1_review/inventory.yaml
stage1_review/cross_reference.yaml
stage1_review/source_spot_check_plan.yaml
```

These files are evidence for the AI review. They are not the final review score.

## Review workflow

### 1. Inventory the artifacts

Create an inventory with counts:

- number of function annotations;
- number of optimization cards;
- number of tunable knobs;
- number of hard constraints;
- number of risk records;
- number of source evidence records;
- whether auxiliary graphs exist: dataflow, pipeline, memory lifetime, workspace layout.

If an expected class is missing, mark it as missing rather than blocking immediately. Continue with partial review.

### 2. Check coverage of required kernel structures

For AscendC FlashAttention / FlashDecode-like operators, Stage-1 extraction should cover these structures:

```text
1. interface / tilingData / workspace input
2. shape/layout: B, S1, S2, N, G, D, varlen, layout conversion
3. multi-core mapping: blockIdx -> batch/head/group/S1/S2/KV split
4. S1/S2 loop or KV-block loop
5. BMM1 / Vec1 / BMM2 / Vec2 pipeline, or decode KV-streaming pipeline
6. UB / L1 / L0 buffer usage
7. L1 residency and L1 partitioning
8. sparse window / causal / band / prefix / mask rules
9. online softmax / LSE state
10. workspace layout and offset uniqueness
11. tail handling and alignment
12. event/wait/flag synchronization
13. scalar computation, offset computation, div/mod/hoist opportunities
14. split-KV, partial output/max/sum, LSE merge for FlashDecode
15. tunable knobs, hard constraints, and forbidden transforms
```

Score coverage by checking whether these structures appear in annotations/cards/auxiliary graphs. Missing L1 residency, workspace layout, event sync, or split-KV merge should be treated as severe for FlashDecode.

### 3. Check accuracy against code facts

For each important artifact, verify against source code when available:

- Is the function role correct?
- Are memory spaces correct: GM, UB, L1, L0A/B/C, workspace?
- Is loop order correct, especially `kv_outer_g_inner` vs `g_outer_kv_inner`?
- Is residency scope correct: per tile, across G, across head, across split?
- Are pipeline dependencies and event waits correct?
- Are constraints derived from real code/API/bug risk rather than guessed?
- Are preconditions sufficient?

If source code is unavailable, mark accuracy confidence as `medium` or `low` and base the score on internal consistency and traceability.

### 4. Check traceability

Important conclusions should cite evidence:

- `file`
- `function` or code region
- observed behavior
- optional line range or symbol name

Every high-value optimization card should have at least one source evidence item. Every tunable knob should point to tilingData, template parameter, constexpr, host tiling, or code variable. Every hard constraint should point to code, API behavior, hardware rule, known bug, or correctness invariant.

### 5. Check DSL-convertibility

For each artifact, ask whether it can directly produce Stage-2 output:

- DSL module candidate
- field candidate
- field type or enum
- searchable knob
- hard validator rule
- lowering pass hint
- forbidden transform or guard

If an artifact is only prose and cannot produce these outputs, mark it as low DSL-convertibility.

### 6. Check risks and negative constraints

Stage-1 must identify what cannot be freely changed. Look for risks such as:

- workspace aliasing;
- online softmax / LSE merge numerical instability;
- event deadlock or missing wait;
- stale L1 resident tile / wrong eviction;
- L1/UB/L0 overflow;
- S2 range or mask semantic breakage;
- tail duplicate-mask error;
- alignment violation;
- split-KV partial result collision;
- invalid loop order for L1 reuse.

If artifacts only say what to optimize but not what to protect, lower the score.

### 7. Check deduplication and naming quality

Look for repeated cards with different names. Canonicalize aliases where possible.

Good card granularity:

- one card = one optimization pattern;
- differences become enum/policy values;
- repeated names become aliases;
- preconditions, risks, DSL fields, and lowering hints are explicit.

Bad granularity:

- one card mixes unrelated patterns;
- every file invents different names for the same idea;
- differences are hidden in prose;
- fields are too source-specific to generalize.

## AI Review Rules

The final score is assigned by the AI reviewer, not by the helper script.

The reviewer must read:

1. `stage1_review/evidence_pack.yaml`
2. `stage1_review/source_spot_check_plan.yaml`
3. high-value referenced artifacts
4. targeted source snippets when source files are available

Use these judgement labels:

- `verified_against_source`
- `supported_by_artifacts_only`
- `not_verifiable`
- `contradicted_or_suspicious`

Do not claim source-level correctness unless source evidence was inspected.

## Scoring rubric: 100 points

Use this scoring table.

| Dimension | Weight | What to evaluate |
|---|---:|---|
| Coverage | 25 | Does extraction cover key FA/FlashDecode structures and optimization patterns? |
| Accuracy | 25 | Does it match source code facts and avoid hallucinated behavior? |
| Traceability | 15 | Can important claims be traced to file/function/code behavior/API/bug evidence? |
| DSL-convertibility | 20 | Can artifacts become DSL module/field/enum/search knob/validator/lowering hint? |
| Risk & constraints | 10 | Are hard constraints, forbidden transforms, and failure modes captured? |
| Dedup & canonicalization | 5 | Are similar patterns merged into stable names and policies? |

### Gate conditions

Even if total score is high, mark Stage-2 readiness as blocked if any of these fail:

```text
coverage < 18 / 25
accuracy < 20 / 25
dsl_convertibility < 15 / 20
important_card_evidence_coverage < 90%
human_spot_check_accuracy < 85%, if spot-check data exists
```

Readiness levels:

```text
85-100: READY_FOR_STAGE2
70-84: READY_WITH_FIXES
50-69: NEEDS_REEXTRACTION
0-49: NOT_USABLE
```

## Output format

Create a review report in Markdown. If writing files, use:

```text
stage1_review/
  score_report.md
  scorecard.yaml
  blocking_findings.yaml
  missing_patterns.yaml
  recommended_fixes.md
  stage2_readiness.yaml
```

The report must include:

1. Executive summary.
2. Overall score and readiness level.
3. Score breakdown table.
4. Gate-condition results.
5. Coverage matrix for the 15 required structures.
6. Top blocking issues.
7. Missing or weak artifacts.
8. Examples of high-quality cards.
9. Examples of weak cards and rewritten versions.
10. Stage-2 input recommendations: which artifacts can be consumed, which must be fixed.

Structured `blocking_findings.yaml` and `missing_patterns.yaml` entries must be actionable by an isolated re-extraction agent. For each issue, include safe fields such as:

```yaml
id:
severity:
dimension:
type:
target_files:
target_symbols:
required_artifacts:
required_evidence:
operator_info_needed:
acceptance_checks:
evidence_class:
```

Use these fields to identify the exact missing or incorrect operator facts that would improve the relevant score dimension. Do not encode long rationale, chain-of-thought, or broad recommendations into structured findings.

## Required judgement style

Be strict. A fluent summary is not enough. Prefer low scores when artifacts are not traceable or not DSL-convertible.

When source code is missing, clearly distinguish:

- `verified_against_source`
- `supported_by_artifacts_only`
- `not_verifiable`

Do not claim source-level correctness unless source evidence was inspected.

## Minimal acceptable artifact schemas

A good `function_annotation` should contain:

```yaml
function_annotation:
  file:
  function:
  role:
  inputs:
  outputs:
  dataflow:
  memory_behavior:
  pipeline_stage:
  tunable_knobs:
  constraints:
  risks:
  possible_dsl_section:
  source_evidence:
```

A good `optimization_card` should contain:

```yaml
optimization_card:
  id:
  canonical_name:
  aliases:
  pattern:
  intent:
  applies_to:
  preconditions:
  tunable_knobs:
  constraints:
  risks:
  possible_dsl_fields:
  lowering_hint:
  source_evidence:
```

## Helper Scripts

Preferred AI-review context preparation:

```bash
python3 scripts/prepare_review_context.py \
  --input <stage1_output_or_.xperf_atdsl_extraction> \
  --output <stage1_output_or_.xperf_atdsl_extraction>/stage1_review
```

Legacy structural pre-score:

```bash
python3 scripts/score_stage1.py \
  --input <stage1_output_or_.xperf_atdsl_extraction> \
  --output <stage1_output_or_.xperf_atdsl_extraction>/stage1_review_legacy
```

`score_stage1.py` is a smoke test only. Do not use it as the final Stage-2 readiness judgement.
