#!/usr/bin/env python3
from __future__ import annotations
import sys, yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load(rel):
    with (ROOT/rel).open('r',encoding='utf-8') as f: return yaml.safe_load(f) or {}

def select_from_list(items,key):
    for item in items:
        if isinstance(item,dict) and (item.get('name')==key or item.get('id')==key or item.get('semantic_id')==key or item.get('region_id')==key): return item
    raise KeyError(f'list item [{key}] not found')

def resolve(obj,path):
    cur=obj
    for part in path.split('.'):
        if '[' in part and part.endswith(']'):
            field,key=part[:-1].split('[',1); cur=cur[field]
            if not isinstance(cur,list): raise KeyError(f'{field} not list')
            cur=select_from_list(cur,key)
        else:
            if not isinstance(cur,dict) or part not in cur: raise KeyError(f'{part} missing')
            cur=cur[part]
    return cur

def main():
    errors=[]
    required=['examples/fused_infer_attention_sink_atdsl_v2.yaml','ir/kernel_ir.schema.yaml','ir/binding_ir.schema.yaml','schedule/schedule_points.yaml','verifier/hardware_verifier.yaml','bindings/reviewed_symbol_binding.fia_sink.yaml','source_refs/stage1_schema_gaps.yaml','source_refs/fia_sink_source_evidence_summary.yaml']
    for rel in required:
        if not (ROOT/rel).exists(): errors.append(f'missing {rel}')
    if errors:
        print('FAIL'); [print('-',e) for e in errors]; return 1
    inst=load('examples/fused_infer_attention_sink_atdsl_v2.yaml')
    sched=load('schedule/schedule_points.yaml').get('schedule_points',[])
    bschema=load('ir/binding_ir.schema.yaml').get('semantic_fields',{})
    reviewed=load('bindings/reviewed_symbol_binding.fia_sink.yaml').get('records',[])
    brec={r.get('semantic_id'):r for r in reviewed}
    # stage1 gap ingestion
    required_paths=['pipeline.stage_graph.owner_identity','mla.nupdate.numeric_contract','flash_decode.metadata_partition','split_core.range_assignment','workspace.mla_tail.binding_status','shape_layout.contract','sparse.policy','scalar.offset_rules']
    gaps=[g.get('path') for g in load('source_refs/stage1_schema_gaps.yaml').get('schema_gaps',[])]
    for p in required_paths:
        if p not in gaps: errors.append(f'stage1 schema gap not preserved: {p}')
    # path resolution + binding coverage
    for item in sched:
        sid=item.get('id'); path=item.get('dsl_path')
        try: resolve(inst,path)
        except Exception as e: errors.append(f'{sid} dsl_path unresolved {path}: {e}')
        sem=item.get('semantic_field')
        if item.get('binding_required'):
            if sem not in bschema: errors.append(f'{sid} missing binding schema for {sem}')
            if sem not in brec: errors.append(f'{sid} missing reviewed binding record for {sem}')
    # required ingested fields
    checks=[
      ('pipeline aliases', lambda: len(inst['kernel_ir']['pipeline']['stage_aliases'])>=2),
      ('fdparams fields', lambda: len(inst['kernel_ir']['flash_decode']['fdparams']['fields'])>=8),
      ('mla tail regions', lambda: len(inst['kernel_ir']['memory_plan']['workspace']['mla_tail_regions']['tail_regions'])>=2),
      ('scalar offset patterns', lambda: len(inst['kernel_ir']['compute']['scalar_offset_rules']['patterns'])>=5),
      ('mla nupdate contract', lambda: 'atomic_target' in inst['kernel_ir']['compute']['mla_nupdate']),
      ('shape layout families', lambda: 'query_layout_families' in inst['semantic_ir']['layout']),
      ('sparse policy modes', lambda: 'mode' in inst['kernel_ir']['sparse_policy']),
    ]
    for name,fn in checks:
        try:
            if not fn(): errors.append(f'missing/weak {name}')
        except Exception as e: errors.append(f'check {name} failed: {e}')
    validators={v.get('id') for v in load('verifier/hardware_verifier.yaml').get('validators',[])}
    for req in ['fd_metadata_bridge_valid','split_core_range_contract_valid','scalar_offset_consistency','mla_nupdate_numeric_contract','mla_tail_budget_stub_valid','shape_layout_contract_valid']:
        if req not in validators: errors.append(f'missing hardware validator {req}')
    # source rewrite safety policy
    for r in reviewed:
        if r.get('state')!='reviewed' and r.get('patch_points'):
            errors.append(f'non-reviewed record has patch_points: {r.get("semantic_id")}')
    if errors:
        print('FAIL ATDSL v0.6 checks')
        for e in errors: print('-',e)
        return 1
    print('PASS ATDSL v0.6 FIA Sink field-completeness checks')
    print(f'schedule_points={len(sched)} binding_schema_fields={len(bschema)} reviewed_records={len(reviewed)} validators={len(validators)}')
    return 0
if __name__=='__main__': raise SystemExit(main())
