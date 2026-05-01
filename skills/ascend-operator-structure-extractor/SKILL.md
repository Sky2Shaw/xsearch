---
name: ascend-operator-structure-extractor
description: Extract structured Stage 1 knowledge from AscendC attention-like operators such as FlashAttention, Sparse FlashAttention, FlashDecode, GQA, MQA, MLA, split-KV decode, and related kernels. Use when Codex needs to analyze mature AscendC operator code, build a full function index, classify function importance, extract optimization cards, tunable knobs, constraints, risks, suggested DSL fields, lowering hints, and project-local learning archives for later ATDSL or performance tuning DSL design. Use especially when the user asks for subagent-based analysis, structured extraction, optimization pattern mining, or DSL input generation from AscendC code.
---

# Ascend Operator Structure Extractor

Use this skill to turn mature AscendC attention-like operator implementations into machine-readable Stage 1 knowledge for later ATDSL/DSL schema design.

Do not rewrite operator code. Do not invent the final DSL. Extract code-backed evidence, optimization cards, constraints, risks, candidate DSL fields, lowering hints, and learning updates.

## Required Reading

Read only the references needed for the current phase:

- `references/workflow.md` for the end-to-end extraction flow.
- `references/subagents.md` when the user asks for subagent-based or parallel analysis.
- `references/prompts.md` before dispatching extraction or aggregation agents.
- `references/schemas.md` before writing YAML artifacts.
- `references/extraction-checklist.md` during AscendC attention analysis.
- `references/evolution-policy.md` before updating `learning/`.

## Core Chain

Always preserve this chain:

```text
source code
  -> full function index
  -> importance scoring
  -> brief extraction
  -> deep extraction
  -> file-level aggregation
  -> operator-level report
  -> DSL candidate sections
  -> schema gaps
  -> learning archive
```

## Function Coverage Policy

Use full shallow scan plus important-function deep extraction.

- Level 0: index every discovered function.
- Level 1: brief-extract potentially relevant helpers.
- Level 2: deep-extract performance-critical functions.
- Gap-driven deepening: after aggregation, upgrade shallow functions when evidence is missing.

Do not deep-extract every function by default. Avoid polluting DSL candidates with ordinary getters, wrappers, logging, or glue code.

## Scripts

Use scripts for deterministic work:

```bash
python3 scripts/init_extraction.py --target-dir <target> --output-root <output>
python3 scripts/build_repo_map.py --target-dir <target> --output-root <output>
python3 scripts/merge_yaml_artifacts.py --output-root <output>
python3 scripts/validate_extraction.py --output-root <output>
```

Scripts do not replace model analysis. They create directories, scan files, score function importance, merge YAML artifacts, and validate structure.

## Subagent Rule

Use subagents only when the user explicitly asks for subagents, delegation, or parallel agent work. Follow `references/subagents.md`. Keep each subagent task bounded and ask for YAML-only output.

## Output Location

By default, write extraction artifacts under the target directory:

```text
.xperf_atdsl_extraction/
```

If the target must not be modified, write to:

```text
/tmp/atdsl_extraction_<operator_name>/
```

## Final Response

After extraction, summarize:

- report path
- files indexed
- functions indexed
- brief and deep extraction counts
- optimization card count
- top 5 DSL candidate sections
- top 5 high-risk constraints
- whether learning items were added
- recommended next step
