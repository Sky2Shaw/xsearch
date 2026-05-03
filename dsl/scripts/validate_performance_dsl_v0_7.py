#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import yaml, sys
ROOT=Path(__file__).resolve().parents[1]
def load(rel): return yaml.safe_load((ROOT/rel).read_text())
def fail(msg): print('FAIL',msg); sys.exit(1)
required_files=[
 'ir/test_contract_ir.schema.yaml','ir/dataflow_ir.schema.yaml','ir/lifetime_ir.schema.yaml','ir/workspace_ir.schema.yaml','ir/memory_copy_ir.schema.yaml','ir/vector_semantics_ir.schema.yaml','ir/split_core_planner_ir.schema.yaml','ir/learning_ir.schema.yaml','ir/risk_ir.schema.yaml','ir/knob_ir.schema.yaml',
 'runtime_ir/test_contract_ir.fia_sink.yaml','runtime_ir/dataflow_ir.fia_sink.yaml','runtime_ir/lifetime_ir.fia_sink.yaml','runtime_ir/workspace_ir.fia_sink.yaml','runtime_ir/memory_copy_ir.common_attention.yaml','runtime_ir/vector_semantics_ir.common_attention.yaml','runtime_ir/split_core_planner_ir.common_attention.yaml','runtime_ir/learning_ir.fia_sink.yaml','runtime_ir/risk_ir.fia_sink.yaml','runtime_ir/knob_ir.fia_sink.yaml']
for f in required_files:
    if not (ROOT/f).exists(): fail(f'missing {f}')
ex=load('examples/fused_infer_attention_sink_atdsl_v2.yaml')
for k in ['test_contract_ir','dataflow_ir','lifetime_ir','workspace_ir','memory_copy_ir','vector_semantics_ir','split_core_planner_ir','learning_ir','risk_ir','knob_ir']:
    if k not in ex: fail(f'example missing {k}')
test=load('runtime_ir/test_contract_ir.fia_sink.yaml'); data=load('runtime_ir/dataflow_ir.fia_sink.yaml'); life=load('runtime_ir/lifetime_ir.fia_sink.yaml'); ws=load('runtime_ir/workspace_ir.fia_sink.yaml'); risks=load('runtime_ir/risk_ir.fia_sink.yaml'); knobs=load('runtime_ir/knob_ir.fia_sink.yaml')
if len(test.get('contracts',[])) < 6: fail('too few test contracts')
if len(data.get('graphs',[])) < 2: fail('too few dataflow graphs')
if len(life.get('items',[])) < 8: fail('too few lifetime items')
if len(ws.get('regions',[])) < 8: fail('too few workspace regions')
if len(risks.get('risks',[])) < 20: fail('too few risks')
if len(knobs.get('knobs',[])) < 7: fail('too few knobs')
sp=load('schedule/schedule_points.yaml')
ids={s['id'] for s in sp.get('schedule_points',[])}
for required in ['sp_workspace_layout_abi_guard','sp_memory_copy_format_guard','sp_vector_invalid_row_guard','sp_split_core_planner_guard']:
    if required not in ids: fail(f'missing schedule point {required}')
validators=[]
for vf in ['verifier/kernel_verifier.yaml','verifier/hardware_verifier.yaml','verifier/lowering_verifier.yaml']:
    d=load(vf)
    for v in d.get('validators',[]): validators.append(v.get('id') if isinstance(v,dict) else v)
for req in ['test_contract_coverage_selected','risk_guard_attached','workspace_layout_abi_valid','dataflow_edge_preserved','lifetime_no_overlap','knob_domain_valid']:
    if req not in validators: fail(f'missing validator {req}')
print(f"PASS ATDSL v0.7 execution-closure checks tests={len(test['contracts'])} dataflow_graphs={len(data['graphs'])} lifetimes={len(life['items'])} workspace_regions={len(ws['regions'])} risks={len(risks['risks'])} knobs={len(knobs['knobs'])} schedule_points={len(sp['schedule_points'])}")
