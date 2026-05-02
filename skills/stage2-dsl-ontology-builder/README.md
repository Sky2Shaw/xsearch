# stage2-dsl-ontology-builder

Codex skill for Stage 2 ATDSL design: convert Stage 1 AscendC FlashAttention/FlashDecode extraction outputs into DSL ontology, schema modules, validators, lowering specs, and shadow DSL examples.

Use in Codex:

```text
$stage2-dsl-ontology-builder
请基于 stage1_outputs 生成 stage2_outputs，并运行质量门禁。
```

Quick scripts:

```bash
python .codex/skills/stage2-dsl-ontology-builder/scripts/bootstrap_stage2.py --input stage1_outputs --output stage2_outputs
python .codex/skills/stage2-dsl-ontology-builder/scripts/check_stage2_quality.py --input stage2_outputs
```
