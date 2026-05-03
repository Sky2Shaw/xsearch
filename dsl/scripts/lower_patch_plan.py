#!/usr/bin/env python3
"""Lower ATDSL transform_trace into a card-aware v0.9 patch_plan.

This is still a scaffold: it emits structured patch plans and execution guards,
not real AscendC diffs. v0.9 adds card_to_dsl_mapping resolution so cards become
executable DSL entry points rather than only knowledge notes.
"""
from __future__ import annotations
import argparse, yaml
from pathlib import Path


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def find_base(path: Path) -> Path:
    cur=path.resolve().parent
    while cur != cur.parent and not (cur/'runtime_ir').exists():
        cur=cur.parent
    return cur


def collect_tests(base_dir: Path, dsl_path: str, semantic_field: str, mapping: dict|None=None):
    required=[]
    if mapping:
        required=list(mapping.get('required_tests') or [])
    p=base_dir/'runtime_ir/test_contract_ir.fia_sink.yaml'
    if not p.exists():
        return [{'id':x,'source':'card_mapping'} for x in required]
    data=load_yaml(p)
    hits=[]
    keys=[dsl_path, semantic_field]
    for c in data.get('contracts',[]):
        covered=c.get('covered_contracts',[])
        if c.get('id') in required or any(k and (k in cc or cc in k) for k in keys for cc in covered):
            hits.append({'id':c['id'],'test_surface':c.get('test_surface'),'file':c.get('file'),'covered_contracts':covered,'source':'card_mapping' if c.get('id') in required else 'dsl_path_match'})
    if not hits:
        broad=[]; combo=(dsl_path+' '+semantic_field).lower()
        if 'workspace' in combo or 'fd' in combo or 'flash' in combo or 's2_base' in combo or 'm_base' in combo or 'tiling' in combo:
            broad+=['TEST-FD-WORKSPACE-TILING','TEST-API-WORKSPACE-SMOKE']
        if 'shape' in combo or 'layout' in combo or 'attention' in combo:
            broad+=['TEST-SHAPE-LAYOUT-FAMILIES']
        if 'sparse' in combo or 'sink' in combo or 's2' in combo:
            broad+=['TEST-SPARSE-SINK-TILING-GUARDS']
        for c in data.get('contracts',[]):
            if c['id'] in broad:
                hits.append({'id':c['id'],'test_surface':c.get('test_surface'),'file':c.get('file'),'covered_contracts':c.get('covered_contracts',[]),'source':'fallback_topic'})
    seen=set(); out=[]
    for h in hits:
        if h['id'] not in seen:
            out.append(h); seen.add(h['id'])
    return out


def collect_risks(base_dir: Path, dsl_path: str, semantic_field: str, mapping: dict|None=None):
    p=base_dir/'runtime_ir/risk_ir.fia_sink.yaml'
    if not p.exists():
        return []
    data=load_yaml(p)
    combo=(dsl_path+' '+semantic_field+' '+' '.join((mapping or {}).get('dsl_paths',[]))).lower()
    hits=[]
    for r in data.get('risks',[]):
        paths=' '.join(r.get('affected_dsl_paths',[])).lower()
        desc=(r.get('description') or '').lower()
        risk_text=paths+' '+desc+' '+ ' '.join(r.get('related_forbidden_transform_ids',[])).lower()
        broad_match=False
        if any(tok in combo for tok in ['workspace','m_base','s2_base','tiling']):
            broad_match = broad_match or any(tok in risk_text for tok in ['workspace','abi','layout','sparse','invalid-row','alignment'])
        if any(tok in combo for tok in ['fd','flash','split_kv']):
            broad_match = broad_match or any(tok in risk_text for tok in ['fd','flash','lse','workspace','task'])
        if any(tok in combo for tok in ['sparse','s2','sink']):
            broad_match = broad_match or any(tok in risk_text for tok in ['sparse','invalid-row','mask','sink'])
        if any(tok in combo for tok in ['l1','event','pipeline','c1','c2','v1','v2']):
            broad_match = broad_match or any(tok in risk_text for tok in ['l1','event','deadlock','runinfo','sync'])
        token_match=any(tok and tok in risk_text for tok in combo.replace('.',' ').replace('_',' ').split())
        if broad_match or token_match:
            hits.append({'id':r['id'],'description':r.get('description'),'verifier_ids':r.get('verifier_ids',[]),'lowering_guard':r.get('lowering_guard')})
    out=[]; seen=set()
    for h in hits:
        if h['id'] not in seen:
            out.append(h); seen.add(h['id'])
    return out[:10]


def collect_knob(base_dir: Path, source_knob: str|None):
    if not source_knob: return []
    p=base_dir/'runtime_ir/knob_ir.fia_sink.yaml'
    if not p.exists(): return []
    data=load_yaml(p)
    return [k for k in data.get('knobs',[]) if k.get('name')==source_knob]


def load_mapping(base: Path, card_id: str|None):
    if not card_id: return None
    p=base/'runtime_ir/card_to_dsl_mapping.fia_sink.yaml'
    if not p.exists():
        raise SystemExit(f'--card-id supplied but mapping file missing: {p}')
    doc=load_yaml(p)
    m=next((x for x in doc.get('mappings',[]) if x.get('card_id')==card_id), None)
    if m is None:
        raise SystemExit(f'Unknown card_id {card_id}')
    return m


def choose_schedule_point(trans: dict, mapping: dict|None):
    sp_id=trans.get('schedule_point') or (trans.get('schedule_points') or [None])[0]
    if not sp_id and mapping:
        sps=mapping.get('schedule_points') or []
        # Prefer a source-rewrite or non-guard schedule point when available; otherwise first.
        sp_id=sps[0] if sps else None
    if not sp_id:
        sp_id=trans.get('id','')
    return sp_id


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--atdsl', required=True)
    ap.add_argument('--transform', required=True)
    ap.add_argument('--card-id', default=None, help='Optional optimization card id. If omitted, transform.card_id is used when present.')
    ap.add_argument('--schedule-points', default='schedule/schedule_points.yaml')
    ap.add_argument('--bindings', default='bindings/reviewed_symbol_binding.fia_sink.yaml')
    ap.add_argument('--out', required=True)
    args=ap.parse_args()
    atdsl_path=Path(args.atdsl)
    base=find_base(atdsl_path)
    trans=load_yaml(Path(args.transform))
    card_id=args.card_id or trans.get('card_id') or trans.get('source_card')
    mapping=load_mapping(base, card_id)
    sp_doc=load_yaml(base/args.schedule_points) if not Path(args.schedule_points).is_absolute() else load_yaml(Path(args.schedule_points))
    sp_id=choose_schedule_point(trans, mapping)
    sp=next((s for s in sp_doc.get('schedule_points',[]) if s.get('id')==sp_id), None)
    if sp is None:
        raise SystemExit(f'Unknown schedule_point {sp_id}')
    # Verify card mapping allows this schedule point.
    if mapping and sp_id not in (mapping.get('schedule_points') or []):
        raise SystemExit(f'schedule_point {sp_id} is not allowed by card {card_id}')
    mode=(mapping or {}).get('lowering_policy') or sp.get('lowering_mode','source_rewrite')
    dsl_path=sp.get('dsl_path'); semantic_field=sp.get('semantic_field')
    mutations=trans.get('mutations') or [{'path':dsl_path,'new_value':trans.get('new_value')}]
    required_tests=collect_tests(base,dsl_path or '',semantic_field or '',mapping)
    risk_guards=collect_risks(base,dsl_path or '',semantic_field or '',mapping)
    knob_checks=collect_knob(base,sp.get('source_knob'))
    # Determine status and rewrites. Contract and planner cards do not directly emit source diff.
    rewrites=[]
    if mode in ('contract_guard_only',) or sp.get('policy')=='fixed_contract':
        status='contract_guards_only'
    elif mode in ('planner_generated_candidate',):
        status='planner_candidate_requires_transform'
    elif mode in ('review_required_patch','guarded_patch_requires_review') or 'review_required' in sp.get('policy',''):
        status='blocked_or_partial_requires_review'
    else:
        status='ready_for_source_diff'
        for i,m in enumerate(mutations):
            rewrites.append({'id':f'rewrite_{i+1}','semantic_field':semantic_field,'dsl_path':m.get('path',dsl_path),'rewrite_kind':'replace_expr','new_value':m.get('new_value'), 'binding_required':sp.get('binding_required',False), 'source_knob':sp.get('source_knob')})
    plan={
        'version':'0.9-card-driven-execution',
        'kind':'atdsl.patch_plan',
        'patch_plan_id':'patch_plan_'+trans.get('id',sp_id),
        'source_transform':trans.get('id'),
        'source_card':card_id,
        'card_mapping': mapping,
        'schedule_point':sp_id,
        'flow_group':sp.get('flow_group') or (mapping or {}).get('flow_group'),
        'semantic_field':semantic_field,
        'dsl_path':dsl_path,
        'lowering_mode':mode,
        'status':status,
        'rewrites':rewrites,
        'contract_guards':sp.get('validators',[]) + ((mapping or {}).get('verifier_ids') or []),
        'required_tests':required_tests,
        'risk_guards':risk_guards,
        'dataflow_guards':(mapping or {}).get('dataflow_guards') or {'source':'runtime_ir/dataflow_ir.fia_sink.yaml','required_when':['fd','workspace','l1','pipeline']},
        'lifetime_guards':(mapping or {}).get('lifetime_guards') or {'source':'runtime_ir/lifetime_ir.fia_sink.yaml','required_when':['workspace','l1','event']},
        'knob_domain_checks':knob_checks,
        'candidate_generation':(mapping or {}).get('candidate_generation'),
        'notes':['v0.9 resolves card_to_dsl_mapping before lowering; real AscendC patch.diff backend is still pending.']
    }
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(yaml.safe_dump(plan,sort_keys=False,allow_unicode=True,width=140))
    print(f"wrote {args.out}: card={card_id} status={status} rewrites={len(rewrites)} tests={len(required_tests)} risks={len(risk_guards)}")

if __name__=='__main__': main()
