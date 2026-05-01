# Subagent Orchestration

Use subagents only when the user explicitly asks for subagents, delegation, or parallel agent work. Otherwise, the main agent performs the workflow directly.

## Main Agent Ownership

The main agent owns:

- Target directory selection and output-root selection.
- Script execution.
- Repo map and function index inspection.
- Subagent task boundaries.
- Result review.
- Merge and validation.
- Final summary to the user.

Subagents assist with read-only extraction, aggregation drafts, and YAML-only artifact content. The main agent is responsible for writing accepted artifacts to disk.

## Dispatch Rules

When the user explicitly requests subagents, prefer subtasks organized by file group or key function group.

Each subagent task must include:

- Exact input files and line ranges.
- Target artifact path where the main agent will save accepted YAML.
- Extraction level and schema to use.
- No duplicate line ranges across subagents unless intentional cross-checking is requested.
- No source code modification.
- YAML-only output for extraction artifacts.
- `unknown` for missing evidence.
- Low confidence for speculation or inference not directly supported by code.

Avoid broad tasks such as "analyze the whole operator" unless the repository is tiny. Keep each task bounded enough that the result can be reviewed against source evidence.

## Recommended Agent Types

- `explorer`: Use for read-only extraction, source inspection, function annotation, file aggregation, operator aggregation drafts, and gap analysis.
- `worker`: Use only when a later task explicitly asks for generated artifact edits. For extraction runs, prefer `explorer` agents and have the main agent write accepted YAML results.

## Extraction Strategy

- Deep extraction is reserved for functions marked `extraction_level: deep` or functions upgraded during gap-driven deepening.
- Brief extraction is suitable for grouped helpers, low-risk wrappers, simple accessors, and secondary utilities.
- Index extraction is mandatory for every discovered function.
- Do not deep-extract large helper groups just because they are nearby; use evidence, importance, and known gap categories.

## Waiting Strategy

The main agent waits for all subagent results before merging. If one subagent is blocked, the main agent records the blocked scope and continues only when the remaining work is independent.

Before accepting a subagent result, the main agent checks:

- Output is valid YAML.
- Output uses the requested schema.
- Source file and line ranges match the assigned scope.
- Claims cite or summarize concrete evidence.
- Missing evidence is represented as `unknown`.
- Confidence values match the strength of evidence.

## Result Handling

Save accepted YAML artifacts under:

- `annotations/functions/brief/`
- `annotations/functions/deep/`
- `annotations/files/`

Then run the merge and validation scripts from the main workflow. The main agent resolves schema errors, duplicate coverage, and unsupported claims before summarizing results.
