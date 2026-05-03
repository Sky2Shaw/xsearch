#!/usr/bin/env python3
from __future__ import annotations
import yaml, sys, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(rel):
    return yaml.safe_load((ROOT/rel).read_text())

def fail(msg):
    print('FAIL',msg)
    sys.exit(1)

def main():
    cards=load('source_refs/cards__optimization_cards.yaml')['optimization_cards']
    card_ids={c['id'] for c in cards}
    sp_doc=load('schedule/schedule_points.yaml')
    sps=sp_doc['schedule_points']
    sp_ids={s['id'] for s in sps}
    mapping=load('runtime_ir/card_to_dsl_mapping.fia_sink.yaml')
    maps=mapping['mappings']
    map_card_ids={m['card_id'] for m in maps}
    if card_ids != map_card_ids:
        fail(f'card mapping mismatch: missing={sorted(card_ids-map_card_ids)} extra={sorted(map_card_ids-card_ids)}')
    for m in maps:
        if not m.get('dsl_paths'): fail(f'{m["card_id"]} has no dsl_paths')
        if not m.get('schedule_points'): fail(f'{m["card_id"]} has no schedule_points')
        for sp in m['schedule_points']:
            if sp not in sp_ids: fail(f'{m["card_id"]} references unknown schedule point {sp}')
        if not m.get('verifier_ids'): fail(f'{m["card_id"]} has no verifier_ids')
        if not m.get('required_tests'): fail(f'{m["card_id"]} has no required_tests')
    # every schedule source card must exist
    for sp in sps:
        for c in sp.get('source_cards',[]):
            if c not in card_ids: fail(f'{sp["id"]} source_card unknown {c}')
    # new v0.9 files exist
    for rel in ['ir/card_to_dsl_mapping.schema.yaml','runtime_ir/card_to_dsl_mapping.fia_sink.yaml','ir/tiling_ir.schema.yaml','runtime_ir/tiling_ir.fia_sink.yaml','runtime_ir/card_driven_schedule_selection.fia_sink.yaml','lowering/examples/patch_plan_card_driven_try_s2_base_128_v0_9.yaml']:
        if not (ROOT/rel).exists(): fail(f'missing {rel}')
    # example lower result should be card-aware and ready for source diff scaffold
    pp=load('lowering/examples/patch_plan_card_driven_try_s2_base_128_v0_9.yaml')
    if pp.get('source_card')!='OC-TILING-SPLIT-CORE-COST-TABLE': fail('example patch plan did not preserve source_card')
    if not pp.get('card_mapping'): fail('example patch plan missing card_mapping')
    if pp.get('status') not in ['ready_for_source_diff','planner_candidate_requires_transform']:
        fail(f'unexpected example status {pp.get("status")}')
    til=load('runtime_ir/tiling_ir.fia_sink.yaml')
    if 'split_core_planner' not in til or 'fd_partition' not in til: fail('tiling_ir missing planner sections')
    print(f'PASS ATDSL v0.9 card-driven execution checks cards={len(cards)} mappings={len(maps)} schedule_points={len(sps)} planner_mappings={sum(1 for m in maps if m.get("candidate_generation"))}')
if __name__=='__main__': main()
