# Evolution Policy

After each operator extraction, update only project-local `.xperf_atdsl_extraction/learning/`. Do not update global skill files unless the user explicitly asks for a skill revision.

## Inputs

Load these prior learning files if present:

- `learned_patterns.yaml`
- `checklist_updates.yaml`
- `negative_lessons.yaml`

Also review the current operator reports, optimization cards, DSL suggestions, constraints, risks, schema gaps, and validation output.

## Deduplication

Deduplicate learning entries by:

- Pattern id.
- Operator family.
- Code evidence.
- DSL field path.
- Optimization intent.

When two entries describe the same pattern with compatible evidence, merge evidence and keep the higher-confidence wording only if justified by source support.

## Conflicts

Preserve conflicting lessons instead of overwriting them.

Use:

```yaml
conflict: true
conflict_reason: string
confidence: high | medium | low
```

Record the operator family, code evidence, and DSL field path for each side of the conflict so later extractions can decide whether the difference is family-specific, architecture-specific, or evidence quality related.

## Allowed Evolution

Evolution may expand:

- Project-local learned pattern libraries.
- Project-local checklist additions.
- Project-local negative lessons.
- Project-local schema gap notes.
- Project-local skill patch proposals.

Evolution must not silently change the final DSL schema. Schema-affecting discoveries belong in `schema_gaps.yaml` or `evolution_patch.yaml` until reviewed.

## Outputs

Write these files under `.xperf_atdsl_extraction/learning/`:

- `learned_patterns.yaml`
- `checklist_updates.yaml`
- `negative_lessons.yaml`
- `evolution_patch.yaml`

Each output entry should include evidence, confidence, and the operator family. Use `unknown` for missing evidence and low confidence for weak inference.
