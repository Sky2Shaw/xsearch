$stage2-dsl-ontology-builder

请基于 stage1_outputs 生成 stage2_outputs。

要求：
1. 先运行 scripts/bootstrap_stage2.py 做二阶段脚手架。
2. 对 stage1_outputs/cards、knobs、constraints、risks、evidence 做人工式归并，不要只保留脚本结果。
3. 重点设计这些模块：decode、l1_partition、l1_residency、workspace、pipeline、sparse_window、tiling、core_mapping。
4. 每个重要字段必须包含 type、enum/candidates、searchable、editable_policy、source_cards、source_evidence、related_validators、lowering_consumers。
5. 每个高风险字段必须有 validator。
6. 生成 fa_forward_shadow.yaml 和 flash_decode_shadow.yaml。
7. 运行 scripts/check_stage2_quality.py。
8. 输出 schema_review.md、coverage_matrix.md、missing_fields.md、quality_gate.json。
