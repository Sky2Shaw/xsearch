# stage2-dsl-ontology-builder

Codex skill for Stage 2 ATDSL design: convert Stage 1 AscendC extraction outputs into DSL ontology, schema modules, validators, lowering specs, and shadow DSL examples.

## New pipeline (evidence-driven)

```bash
# Step 1: Parse Stage 1 YAML into EvidenceGraph
python scripts/stage2_parser.py --input stage1_outputs --output stage2_outputs/.evidence_graph.json

# Step 2: Generate all Stage 2 artifacts from the graph
python scripts/stage2_synthesizer.py --evidence-graph stage2_outputs/.evidence_graph.json --output stage2_outputs

# Step 3: Run semantic quality gate
python scripts/stage2_verifier.py --evidence-graph stage2_outputs/.evidence_graph.json --stage2-dir stage2_outputs
```

## Legacy entrypoints (deprecated, delegates to new pipeline)

```bash
python scripts/bootstrap_stage2.py --input stage1_outputs --output stage2_outputs
python scripts/check_stage2_quality.py --input stage2_outputs
```

## Stage 2 v0.4 agent-ready contracts

The synthesizer now emits additional contracts for later agent search and replay:

- `ir/semantic_ir.yaml`
- `ir/kernel_ir.yaml`
- `ir/hardware_contract.yaml`
- `ir/execution_feedback.yaml`
- `search/schedule_space.yaml`
- `search/feature_schema.yaml`
- `search/measurement_schema.yaml`
- `search/tuning_record.schema.yaml`

These files describe the DSL action space, hardware assumptions, feature schema, metric schema, and replay record format. They do not compile kernels or report measured performance.
