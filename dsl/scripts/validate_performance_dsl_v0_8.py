#!/usr/bin/env python3
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
card_file = ROOT / "source_refs" / "cards__optimization_cards.yaml"
data = yaml.safe_load(card_file.read_text())
cards = data.get("optimization_cards", [])
flow_groups = {g["id"] for g in data.get("flow_groups", [])}
ids = [c.get("id") for c in cards]
errors = []
if len(ids) != len(set(ids)):
    errors.append("duplicate card ids found")
required = ["id","canonical_name","title","flow_group","card_type","pipeline_position","granularity","applies_to","pattern_summary","optimization_intent","preconditions","constraints","risks","possible_dsl_fields","lowering_hint","source_evidence","confidence","agent_usage"]
for c in cards:
    missing = [k for k in required if k not in c]
    if missing:
        errors.append(f"{c.get('id')}: missing {missing}")
    if c.get("flow_group") not in flow_groups:
        errors.append(f"{c.get('id')}: unknown flow_group {c.get('flow_group')}")

def count_group(name):
    return sum(1 for c in cards if c.get("flow_group") == name)

if len(cards) < 28:
    errors.append(f"expected at least 28 cards, got {len(cards)}")
for g in ["HOST_API","TILING_SPLIT_CORE","C1","V1","C2","V2","FLASH_DECODE"]:
    if count_group(g) == 0:
        errors.append(f"missing cards for flow group {g}")

needed_tiling = {
    "OC-TILING-SPLIT-CORE-COST-TABLE",
    "OC-TILING-USED-CORE-SEARCH-BOUNDS",
    "OC-TILING-FD-GS1-PARTITION-SEARCH",
    "OC-TILING-SPARSE-SINK-PRE-NEXT-TOKEN-RANGES",
}
missing_tiling = needed_tiling - set(ids)
if missing_tiling:
    errors.append(f"missing tiling split-core cards: {sorted(missing_tiling)}")

for required_file in [
    ROOT / "ir" / "card_ir.schema.yaml",
    ROOT / "runtime_ir" / "card_flow_taxonomy.fia_sink.yaml",
    ROOT / "reports" / "card_coverage_matrix_v0_8.yaml",
]:
    if not required_file.exists():
        errors.append(f"missing {required_file.relative_to(ROOT)}")

if errors:
    print("FAIL ATDSL v0.8 card-flow taxonomy checks")
    for e in errors:
        print("-", e)
    sys.exit(1)

print("PASS ATDSL v0.8 card-flow taxonomy checks")
print(f"cards={len(cards)} flow_groups={len(flow_groups)} tiling_cards={count_group('TILING_SPLIT_CORE')}")
