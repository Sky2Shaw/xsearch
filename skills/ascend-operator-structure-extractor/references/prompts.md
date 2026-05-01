# Prompt Templates

- [Function Brief Extraction](#function-brief-extraction)
- [Function Deep Extraction](#function-deep-extraction)
- [File Aggregation](#file-aggregation)
- [Operator Aggregation](#operator-aggregation)
- [Evolution](#evolution)
- [Gap-Driven Deepening](#gap-driven-deepening)

These templates are for bounded extraction work. Each prompt requires YAML-only output, no source code modification, `unknown` for missing evidence, and low confidence for speculation.

## Function Brief Extraction

```text
You are extracting a brief function annotation for an AscendC attention-like operator.

Scope:
- Function: {qualified_name}
- File: {file}
- Line range: {line_range}
- Allowed context: only the provided function body, nearby declarations, and explicitly supplied call graph entries.

Rules:
- Output YAML only.
- Do not modify source code.
- Do not analyze outside the bounded scope.
- Preserve the supplied canonical/template identity; do not merge this function with same-name functions owned by other template classes or variants.
- Use unknown for missing evidence.
- Use low confidence for speculation or weak inference.
- Do not invent DSL fields, optimization patterns, constraints, or risks.

Schema: function_brief

Focus:
- Role in the operator.
- Tensors, buffers, queues, tiling data, workspace, flags, and scalar state touched.
- Calls and called-by context.
- Possible risks.
- Related DSL sections.
- Whether deep extraction is needed and why.
```

## Function Deep Extraction

```text
You are extracting a deep function annotation for an AscendC attention-like operator.

Scope:
- Function: {qualified_name}
- File: {file}
- Line range: {line_range}
- Allowed context: only the provided function body, directly referenced declarations, supplied type definitions, and explicitly supplied call graph entries.

Rules:
- Output YAML only.
- Do not modify source code.
- Do not analyze outside the bounded scope.
- Preserve the supplied canonical/template identity; if this is a wrapper around a stage body such as `ProcessMm2`, record the delegated body as a required deepening target.
- Use unknown for missing evidence.
- Use low confidence for speculation or weak inference.
- Do not invent DSL fields, optimization patterns, constraints, risks, or lowering hints.

Schema: function_annotation

Extract:
- Role and confidence.
- Code behavior.
- Dataflow inputs and outputs.
- GM, UB, L1, L0A, L0B, and L0C behavior.
- Control flow, including loops and branches.
- Pipeline stages and synchronization.
- Tiling and shape handling.
- Workspace layout or offsets.
- Tail and alignment behavior.
- Scalar computation and constexpr computation.
- Tunable knobs and structural fields.
- Hard constraints.
- Risks if changed.
- Possible DSL fields.
- Lowering hints supported by evidence.
```

## File Aggregation

```text
You are aggregating function annotations into one file-level analysis for an AscendC attention-like operator.

Scope:
- File: {file}
- Function artifacts: {artifact_list}
- Allowed context: provided index, brief, and deep annotations for this file plus directly supplied source snippets.

Rules:
- Output YAML only.
- Do not modify source code.
- Do not analyze outside the bounded file scope.
- Use unknown for missing evidence.
- Use low confidence for speculation or weak inference.
- Do not invent patterns.

Schema: file_analysis

Extract:
- File role.
- Important functions.
- Variant-specific stage coverage, especially separate MM1/MM2/PV implementations for GQA, MLA, FlashDecode, and generic nonquant paths when present.
- File-level dataflow.
- File-level pipeline.
- Memory strategy.
- L1 strategy.
- Decode strategy.
- Optimization cards.
- Tunable knobs.
- Constraints.
- Risks.
- Suggested DSL sections.

Optimization card criteria:
- Create a card only when at least two of these are true: performance relevance, reusable pattern, tunable parameter, hard constraint, correctness risk, DSL mapping, lowering impact, or stable mature-code pattern.
- Do not create cards for trivial wrappers, one-off code with no reuse signal, unsupported guesses, or behavior already represented only as a basic field.
```

## Operator Aggregation

```text
You are aggregating file-level analyses into an operator-level structure report.

Scope:
- Operator family: {operator_family}
- Target root: {target_root}
- File artifacts: {file_artifacts}
- Allowed context: provided repo map, function index, file analyses, and supplied learning files.

Rules:
- Output YAML only unless explicitly asked for Markdown.
- Do not modify source code.
- Do not analyze outside the provided artifacts.
- Use unknown for missing evidence.
- Use low confidence for speculation or weak inference.
- Do not invent patterns, DSL fields, constraints, risks, or lowering hints.

Schema: analysis_result

Extract:
- Metadata and coverage.
- Operator summary.
- Files analyzed.
- Optimization cards.
- Tunable knobs.
- Constraints.
- Risks.
- Suggested DSL sections.
- Lowering hints.
- Open questions and evidence gaps.
```

## Evolution

```text
You are updating project-local extraction learning after an operator analysis.

Scope:
- Operator family: {operator_family}
- Output root: {output_root}
- Current reports: {report_paths}
- Prior learning files: {learning_paths}

Rules:
- Output YAML only.
- Do not modify source code.
- Update only project-local learning artifacts under .xperf_atdsl_extraction/learning/.
- Use unknown for missing evidence.
- Use low confidence for speculation or weak inference.
- Deduplicate by pattern id, operator family, code evidence, DSL field path, and optimization intent.
- Preserve conflicts with conflict: true, conflict_reason, and confidence.
- Do not silently change the final DSL schema.

Schema: evolution_result

Extract:
- New patterns.
- Updated patterns.
- Checklist updates.
- Negative lessons.
- Schema gaps.
- Skill patch proposal.
```

## Gap-Driven Deepening

```text
You are identifying functions that need upgraded extraction because important operator evidence is missing.

Scope:
- Current gaps: {gap_list}
- Function index: {function_index}
- Allowed search terms: Offset, Workspace, Addr, Address, Calc, Compute, ComputeMm1, ComputeMm2, ProcessMm1, ProcessMm2, Bmm1, Bmm2, Range, Loop, Tail, Align, Mask, BlockTable, Kv, Cache, Split, Merge, Lse.

Rules:
- Output YAML only.
- Do not modify source code.
- Do not analyze outside the provided index and gap list.
- Use unknown for missing evidence.
- Use low confidence for speculation or weak inference.
- Recommend brief or deep upgrades only when tied to a specific gap and function evidence.

Output:
- functions_to_upgrade:
  - qualified_name
  - file
  - line_range
  - current_extraction_level
  - recommended_extraction_level
  - gap_addressed
  - evidence
  - confidence
```
