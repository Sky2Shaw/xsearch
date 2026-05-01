# Workflow

- [Phase 0 Setup](#phase-0-setup)
- [Phase 1 Full Inventory](#phase-1-full-inventory)
- [Phase 2 Importance-Based Extraction](#phase-2-importance-based-extraction)
- [Phase 3 File Aggregation](#phase-3-file-aggregation)
- [Phase 4 Operator Aggregation](#phase-4-operator-aggregation)
- [Phase 5 Gap-Driven Deepening](#phase-5-gap-driven-deepening)
- [Phase 6 Evolution](#phase-6-evolution)
- [Phase 7 Validation](#phase-7-validation)

Use this workflow for structured extraction from mature AscendC attention-like operators. Keep every claim tied to code evidence. Do not invent patterns, constraints, or DSL fields when the source does not support them; write `unknown` instead.

## Phase 0 Setup

- Identify the target operator directory and confirm the analysis boundary.
- Choose an output root, normally `.xperf_atdsl_extraction/` under the project being analyzed unless the user requests another location.
- Run `scripts/init_extraction.py` to create the extraction workspace.
- Load prior learning files if present under the output root learning directory:
  - `learning/learned_patterns.yaml`
  - `learning/checklist_updates.yaml`
  - `learning/negative_lessons.yaml`

## Phase 1 Full Inventory

- Run `scripts/build_repo_map.py` against the target directory and output root.
- Produce these inventory artifacts:
  - `repo_map.yaml`
  - `file_inventory.yaml`
  - `function_index.yaml`
  - `function_importance.yaml`
  - `skipped_or_shallow_items.yaml`
  - `annotations/functions/index/*.yaml`
- Every discovered function must receive an index entry, even if it is later marked shallow, skipped, or low importance.
- Index entries must preserve file path, line range, calls, called-by evidence when available, rough role, importance score, importance reasons, and extraction level.
- For C++ template and out-of-class method definitions, preserve `canonical_name`, `owner`, `owner_qualified`, `owner_template_args`, `template_params`, `variant`, and `stage`; do not collapse distinct template owners such as GQA and MLA into a bare `ComputeMm2`.

## Phase 2 Importance-Based Extraction

Use extraction levels consistently:

- `index`: basic function record only.
- `brief`: concise role, touch points, call context, risks, related DSL areas, and whether deep extraction is needed.
- `deep`: full behavior annotation with dataflow, control flow, memory, pipeline, tiling, workspace, constraints, risks, DSL fields, and lowering hints.

Deep-extract functions whose names, qualified names, comments, or surrounding call context match these attention-critical patterns:

- `Init`
- `InitBuffer`
- `Process`
- `ComputeMm1`
- `ComputeMm2`
- `ProcessMm1`
- `ProcessMm2`
- `ComputeConstexpr`
- `ComputeAxisIdx`
- `GetS2LoopRange`
- `SetExtraInfo`
- `IterateBmm1`
- `IterateBmm2`
- `ProcessVec1`
- `ProcessVec2`
- `DataCopy`
- `WorkspaceOffset`
- `BlockTable`
- `KvCache`
- `SplitKv`
- `LseMerge`
- `Softmax`

For attention-like kernels, deep coverage is stage-based as well as score-based. Each concrete implementation variant visible in the target, such as GQA, MLA, FlashDecode, or generic nonquant, must deep-extract its main `mm1`, `vec1`, `mm2`, and output/merge path when present. If a stage is intentionally skipped, record an explicit gap with file and line evidence.

Use brief extraction for grouped helpers unless gap-driven deepening upgrades them.

## Phase 3 File Aggregation

Aggregate `index`, `brief`, and `deep` function artifacts into file-level YAML under `annotations/files/`.

For each file, extract:

- File role.
- Important functions and why they matter.
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

Create optimization cards only when supported by concrete code evidence.

## Phase 4 Operator Aggregation

Aggregate file-level artifacts into operator-level outputs:

- `reports/operator_structure_report.yaml`
- `reports/operator_structure_report.md`
- `cards/optimization_cards.yaml`
- `dsl/suggested_dsl_sections.yaml`
- `dsl/schema_gaps.yaml`
- `knobs/tunable_knobs.yaml`
- `constraints/constraints.yaml`
- `risks/risks.yaml`

Do not invent patterns. If evidence is missing or contradictory, record the gap, confidence, and source locations instead of filling it in.

## Phase 5 Gap-Driven Deepening

If evidence lacks coverage for workspace layout, KV cache, L1 residency, split-KV, LSE merge, sparse window, tail handling, alignment, event scheduling, MM1/MM2 stage behavior, or related high-risk behavior, search `function_index.yaml` for functions containing:

- `Offset`
- `Workspace`
- `Addr`
- `Address`
- `Calc`
- `Compute`
- `Range`
- `Loop`
- `Tail`
- `Align`
- `Mask`
- `BlockTable`
- `Kv`
- `Cache`
- `Split`
- `Merge`
- `Lse`

Upgrade matching functions to `brief` or `deep` extraction according to risk and evidence needs. Re-run file and operator aggregation after upgrades.

## Phase 6 Evolution

Update learning under `learning/` according to `evolution-policy.md`.

Evolution may add project-local patterns, checklist updates, negative lessons, and patch proposals. It must not silently change the final DSL schema.

## Phase 7 Validation

- Run `scripts/merge_yaml_artifacts.py`.
- Run `scripts/validate_extraction.py`.
- Review validation output and fix generated extraction artifacts as needed.
- Summarize coverage, important gaps, confidence, and any validation issues in the final response.
