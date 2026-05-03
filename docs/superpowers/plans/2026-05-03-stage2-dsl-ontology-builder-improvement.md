# Stage 2 DSL Ontology Builder Skill Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hard-coded template-based Stage 2 generation with an evidence-driven three-layer pipeline: EvidenceGraph Builder (parser), Synthesizer, and Semantic Verifier.

**Architecture:** Parser reads structured Stage 1 YAML into a typed graph (EvidenceGraph). Synthesizer traverses the graph to infer modules, generate schema fields, derive validators, and emit shadow DSL. Verifier checks the output semantically against the graph (evidence connectivity, field completeness, validator coverage, shadow DSL coverage). All three layers are independent scripts that can run alone.

**Tech Stack:** Python 3.11, PyYAML, standard library only (no external deps).

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/stage2_parser.py` | Parse Stage 1 YAML into `.evidence_graph.json` |
| `scripts/stage2_synthesizer.py` | Read EvidenceGraph, emit all `stage2_outputs/` artifacts |
| `scripts/stage2_verifier.py` | Read EvidenceGraph + `stage2_outputs/`, emit `review/quality_gate.json` |
| `scripts/module_inference_rules.yaml` | Configurable mapping from `dsl_field.path` token to ontology module |
| `tests/fixtures/` | Minimal Stage 1 YAML files for unit testing |
| `tests/test_parser.py` | Unit tests for parser |
| `tests/test_synthesizer.py` | Unit tests for synthesizer |
| `tests/test_verifier.py` | Unit tests for verifier |
| `SKILL.md` | Updated workflow and agent definitions |
| `README.md` | Updated quick-start commands |
| `references/output_contract.md` | Extended `quality_gate.json` contract |
| `scripts/bootstrap_stage2.py` | Deprecation shim (delegate to new pipeline) |
| `scripts/check_stage2_quality.py` | Deprecation shim (delegate to new verifier) |

---

### Task 1: Parser — Core Models and EvidenceGraph Builder

**Files:**
- Create: `skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py`
- Test: `skills/stage2-dsl-ontology-builder/tests/test_parser.py`

- [ ] **Step 1: Create test fixtures directory and minimal YAML fixtures**

Create directory: `skills/stage2-dsl-ontology-builder/tests/fixtures/`

Create `tests/fixtures/cards.yaml`:
```yaml
optimization_cards:
  - id: OC-TEST-CARD-1
    canonical_name: test.card.one
    aliases: [test_card_alias]
    title: Test card for parser
    applies_to:
      variants: [nonquant]
      owners: [TestOwner]
      stages: [test.stage]
    pattern_summary: Test pattern summary
    optimization_intent: Test intent
    preconditions: []
    tunable_knobs: [testKnob]
    constraints: [C-TEST-1]
    risks: [R-TEST-1]
    possible_dsl_fields:
      - path: tiling.s1_base
        meaning: Base S1 tile size in tokens
        confidence: high
      - path: pipeline.kind
        meaning: Pipeline variant kind
        confidence: medium
    source_evidence:
      - id: SE-TEST-1
        role: test evidence for card
    confidence: high
```

Create `tests/fixtures/evidence.yaml`:
```yaml
source_evidence:
  - id: SE-TEST-1
    artifact_ids: []
    file: test/file.h
    symbol: TestFunction
    line_range:
      start: 1
      end: 10
    observed_fact: Test observed fact
    confidence: high
```

Create `tests/fixtures/constraints.yaml`:
```yaml
constraints:
  - id: C-TEST-1
    description: Test constraint description
    evidence: reports/function_index.yaml
    source_evidence_ids:
      - SE-TEST-1
    related_forbidden_transform_ids:
      - FT-TEST-1
forbidden_transforms:
  - id: FT-TEST-1
    scope: test.scope
    forbidden_change: Do not change this test thing
    affected_artifacts: []
    source_evidence_ids:
      - SE-TEST-1
```

Create `tests/fixtures/risks.yaml`:
```yaml
risks:
  - id: R-TEST-1
    description: Test risk description
    evidence: test/file.h
    related_forbidden_transform_ids:
      - FT-TEST-1
```

Create `tests/fixtures/knobs.yaml`:
```yaml
tunable_knobs:
  - name: testKnob
    type: integer
    domain:
      kind: positive_integer
      minimum: 1
      unit: tokens
    applies_to:
      variants: [nonquant]
      owners: [TestOwner]
      consumers: []
    default_behavior:
      source: host tiling
      fixed_or_derived: host_selected
    coupled_constraints:
      - C-TEST-1
    searchable: true
    source_evidence:
      - id: SE-TEST-1
```

Create `tests/fixtures/pipeline_graphs.yaml`:
```yaml
pipeline_graphs:
  schema_version: 1
  graphs:
    - id: graph.test.main
      variant: nonquant
      description: Test pipeline
      preload_scheduler:
        pattern: current.mm1 -> older.vec1
        source_evidence_ids:
          - SE-TEST-1
      nodes:
        - id: test.mm1
          stage: test.mm1
          canonical_name: TestOwner::ComputeMm1
          owner: TestOwner
          role: Test MM1 stage
      edges: []
```

Create `tests/fixtures/workspace_layout.yaml`:
```yaml
workspace_layout:
  schema_version: 1
  regions:
    - region_id: normal.mm1
      family: normal
      region_name: mm1
      binding_status: explicit_kernel_gm
      enabled_when: Always
      element_type: float32
      size_formula: slots * coreNum * size
      base_offset_rule: Starts at 0
      byte_order_rule: row-major
      producer_functions:
        - TestOwner::ComputeMm1
      consumer_functions:
        - TestOwner::ProcessVec1
      aliasing_rule: Dedicated
      confidence: high
      source_evidence_ids:
        - SE-TEST-1
```

Create `tests/fixtures/suggested_dsl_sections.yaml`:
```yaml
suggested_dsl_sections:
  - name: tiling
    purpose: Test tiling section
    fields:
      - path: tiling.s1_base
        meaning: Base S1 tile size
        evidence: test/file.h
        confidence: high
```

- [ ] **Step 2: Write failing test for parser loading**

Create `tests/test_parser.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import parse_stage1, EvidenceGraph


def test_parse_cards():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    assert graph is not None
    assert len(graph.nodes) > 0
```

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_parser.py::test_parse_cards -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'stage2_parser'`

- [ ] **Step 3: Implement EvidenceGraph dataclass and parser skeleton**

Create `scripts/stage2_parser.py`:
```python
#!/usr/bin/env python3
"""Parse Stage 1 structured YAML into an EvidenceGraph."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EvidenceNode:
    id: str
    kind: str
    data: dict[str, Any]


@dataclass
class EvidenceEdge:
    from_id: str
    to_id: str
    label: str


@dataclass
class EvidenceGraph:
    nodes: list[EvidenceNode] = field(default_factory=list)
    edges: list[EvidenceEdge] = field(default_factory=list)

    def add_node(self, node: EvidenceNode) -> None:
        self.nodes.append(node)

    def add_edge(self, edge: EvidenceEdge) -> None:
        self.edges.append(edge)

    def get_node(self, node_id: str) -> EvidenceNode | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [{"id": n.id, "kind": n.kind, "data": n.data} for n in self.nodes],
            "edges": [{"from": e.from_id, "to": e.to_id, "label": e.label} for e in self.edges],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> EvidenceGraph:
        raw = json.loads(path.read_text(encoding="utf-8"))
        graph = cls()
        for n in raw["nodes"]:
            graph.add_node(EvidenceNode(id=n["id"], kind=n["kind"], data=n["data"]))
        for e in raw["edges"]:
            graph.add_edge(EvidenceEdge(from_id=e["from"], to_id=e["to"], label=e["label"]))
        return graph


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _add_card_nodes(graph: EvidenceGraph, cards_data: Any) -> None:
    for card in cards_data.get("optimization_cards", []):
        card_id = card["id"]
        graph.add_node(EvidenceNode(id=card_id, kind="card", data=card))

        for dsl_ref in card.get("possible_dsl_fields", []):
            field_path = dsl_ref["path"]
            field_id = f"field:{field_path}"
            if graph.get_node(field_id) is None:
                graph.add_node(EvidenceNode(id=field_id, kind="dsl_field", data=dsl_ref))
            graph.add_edge(EvidenceEdge(from_id=card_id, to_id=field_id, label="suggests"))

        for ev_ref in card.get("source_evidence", []):
            ev_id = ev_ref["id"]
            graph.add_edge(EvidenceEdge(from_id=card_id, to_id=ev_id, label="backed_by"))

        for c_id in card.get("constraints", []):
            graph.add_edge(EvidenceEdge(from_id=card_id, to_id=c_id, label="constrained_by"))

        for r_id in card.get("risks", []):
            graph.add_edge(EvidenceEdge(from_id=card_id, to_id=r_id, label="risked_by"))


def _add_evidence_nodes(graph: EvidenceGraph, evidence_data: Any) -> None:
    for ev in evidence_data.get("source_evidence", []):
        ev_id = ev["id"]
        if graph.get_node(ev_id) is None:
            graph.add_node(EvidenceNode(id=ev_id, kind="evidence", data=ev))


def _add_constraint_nodes(graph: EvidenceGraph, constraints_data: Any) -> None:
    for c in constraints_data.get("constraints", []):
        c_id = c["id"]
        if graph.get_node(c_id) is None:
            graph.add_node(EvidenceNode(id=c_id, kind="constraint", data=c))
        for ft_id in c.get("related_forbidden_transform_ids", []):
            graph.add_edge(EvidenceEdge(from_id=c_id, to_id=ft_id, label="forbids"))
        for ev_id in c.get("source_evidence_ids", []):
            graph.add_edge(EvidenceEdge(from_id=c_id, to_id=ev_id, label="backed_by"))

    for ft in constraints_data.get("forbidden_transforms", []):
        ft_id = ft["id"]
        if graph.get_node(ft_id) is None:
            graph.add_node(EvidenceNode(id=ft_id, kind="forbidden_transform", data=ft))
        for ev_id in ft.get("source_evidence_ids", []):
            graph.add_edge(EvidenceEdge(from_id=ft_id, to_id=ev_id, label="backed_by"))


def _add_risk_nodes(graph: EvidenceGraph, risks_data: Any) -> None:
    for r in risks_data.get("risks", []):
        r_id = r["id"]
        if graph.get_node(r_id) is None:
            graph.add_node(EvidenceNode(id=r_id, kind="risk", data=r))
        for ft_id in r.get("related_forbidden_transform_ids", []):
            graph.add_edge(EvidenceEdge(from_id=r_id, to_id=ft_id, label="forbids"))


def _add_knob_nodes(graph: EvidenceGraph, knobs_data: Any) -> None:
    for k in knobs_data.get("tunable_knobs", []):
        k_name = k["name"]
        k_id = f"knob:{k_name}"
        if graph.get_node(k_id) is None:
            graph.add_node(EvidenceNode(id=k_id, kind="knob", data=k))
        for c_id in k.get("coupled_constraints", []):
            graph.add_edge(EvidenceEdge(from_id=k_id, to_id=c_id, label="couples_to"))


def _add_pipeline_nodes(graph: EvidenceGraph, pipeline_data: Any) -> None:
    for g in pipeline_data.get("pipeline_graphs", {}).get("graphs", []):
        for node in g.get("nodes", []):
            node_id = node["id"]
            if graph.get_node(node_id) is None:
                graph.add_node(EvidenceNode(id=node_id, kind="pipeline_node", data=node))
            for ev_id in node.get("source_evidence_ids", []):
                graph.add_edge(EvidenceEdge(from_id=node_id, to_id=ev_id, label="backed_by"))


def _add_workspace_nodes(graph: EvidenceGraph, workspace_data: Any) -> None:
    for region in workspace_data.get("workspace_layout", {}).get("regions", []):
        region_id = region["region_id"]
        if graph.get_node(region_id) is None:
            graph.add_node(EvidenceNode(id=region_id, kind="workspace_region", data=region))
        for ev_id in region.get("source_evidence_ids", []):
            graph.add_edge(EvidenceEdge(from_id=region_id, to_id=ev_id, label="backed_by"))


def _add_suggested_section_nodes(graph: EvidenceGraph, sections_data: Any) -> None:
    for sec in sections_data.get("suggested_dsl_sections", []):
        sec_name = sec["name"]
        sec_id = f"section:{sec_name}"
        if graph.get_node(sec_id) is None:
            graph.add_node(EvidenceNode(id=sec_id, kind="suggested_section", data=sec))


def _link_fields_to_knobs(graph: EvidenceGraph) -> None:
    """Create tuned_by edges from dsl_field to knob when knob name matches field path or meaning."""
    field_nodes = [n for n in graph.nodes if n.kind == "dsl_field"]
    knob_nodes = [n for n in graph.nodes if n.kind == "knob"]

    for field_node in field_nodes:
        path = field_node.data.get("path", "")
        meaning = field_node.data.get("meaning", "")
        path_last = path.split(".")[-1] if "." in path else path

        for knob_node in knob_nodes:
            knob_name = knob_node.data.get("name", "")
            if knob_name == path_last:
                graph.add_edge(EvidenceEdge(from_id=field_node.id, to_id=knob_node.id, label="tuned_by"))
                continue
            if knob_name and f" {knob_name} " in f" {meaning} ":
                graph.add_edge(EvidenceEdge(from_id=field_node.id, to_id=knob_node.id, label="tuned_by"))


def parse_stage1(input_dir: Path) -> EvidenceGraph:
    graph = EvidenceGraph()

    files = {
        "cards": input_dir / "cards" / "optimization_cards.yaml",
        "evidence": input_dir / "evidence" / "source_evidence.yaml",
        "constraints": input_dir / "constraints" / "constraints.yaml",
        "risks": input_dir / "risks" / "risks.yaml",
        "knobs": input_dir / "knobs" / "tunable_knobs.yaml",
        "pipeline": input_dir / "auxiliary" / "pipeline_graphs.yaml",
        "workspace": input_dir / "auxiliary" / "workspace_layout.yaml",
        "sections": input_dir / "dsl" / "suggested_dsl_sections.yaml",
    }

    data = {k: _load_yaml(v) for k, v in files.items()}

    _add_evidence_nodes(graph, data["evidence"] or {})
    _add_card_nodes(graph, data["cards"] or {})
    _add_constraint_nodes(graph, data["constraints"] or {})
    _add_risk_nodes(graph, data["risks"] or {})
    _add_knob_nodes(graph, data["knobs"] or {})
    _add_pipeline_nodes(graph, data["pipeline"] or {})
    _add_workspace_nodes(graph, data["workspace"] or {})
    _add_suggested_section_nodes(graph, data["sections"] or {})
    _link_fields_to_knobs(graph)

    return graph


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="stage1_outputs")
    parser.add_argument("--output", default="stage2_outputs/.evidence_graph.json")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    graph = parse_stage1(input_dir)
    graph.save(output_path)
    print(f"EvidenceGraph saved to {output_path} ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run parser test to verify it passes**

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_parser.py::test_parse_cards -v`

Expected: PASS

- [ ] **Step 5: Add connectivity test**

Append to `tests/test_parser.py`:
```python
def test_card_evidence_connectivity():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)

    card_node = graph.get_node("OC-TEST-CARD-1")
    assert card_node is not None

    # Card should have edge to evidence SE-TEST-1
    ev_edges = [e for e in graph.edges if e.from_id == "OC-TEST-CARD-1" and e.to_id == "SE-TEST-1"]
    assert len(ev_edges) == 1
    assert ev_edges[0].label == "backed_by"


def test_field_knob_link():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)

    field_id = "field:tiling.s1_base"
    knob_id = "knob:testKnob"
    tuned_edges = [e for e in graph.edges if e.from_id == field_id and e.to_id == knob_id]
    assert len(tuned_edges) == 1
    assert tuned_edges[0].label == "tuned_by"


def test_graph_save_load():
    import tempfile
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = Path(f.name)

    graph.save(path)
    loaded = EvidenceGraph.load(path)
    assert len(loaded.nodes) == len(graph.nodes)
    assert len(loaded.edges) == len(graph.edges)
    path.unlink()
```

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_parser.py -v`

Expected: all 4 tests PASS

- [ ] **Step 6: Commit parser**

```bash
git add skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py \
        skills/stage2-dsl-ontology-builder/tests/ \
        skills/stage2-dsl-ontology-builder/tests/fixtures/
git commit -m "$(cat <<'EOF'
feat: Stage 2 EvidenceGraph parser with structured YAML parsing

- Parse cards, evidence, constraints, risks, knobs, pipeline, workspace
- Build typed node/edge graph with cross-references
- Link dsl_fields to knobs via path/meaning matching
- Save/load as JSON intermediate representation
- Unit tests with minimal fixtures

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Synthesizer — Module Inference and Schema Generation

**Files:**
- Create: `skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py`
- Create: `skills/stage2-dsl-ontology-builder/scripts/module_inference_rules.yaml`
- Test: `skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py`

- [ ] **Step 1: Create module inference rules file**

Create `scripts/module_inference_rules.yaml`:
```yaml
version: "1.0"
fallback: needs_review
rules:
  - token: kernel
    module: kernel
  - token: target
    module: target
  - token: features
    module: features
  - token: interface
    module: interface
  - token: shape
    module: shape
  - token: shape_layout
    module: shape
  - token: layout
    module: layout
  - token: tiling
    module: tiling
  - token: core_mapping
    module: core_mapping
  - token: memory
    module: memory
  - token: l1_partition
    module: l1_partition
  - token: l1_residency
    module: l1_residency
  - token: workspace
    module: workspace
  - token: pipeline
    module: pipeline
  - token: decode
    module: decode
  - token: flash_decode
    module: decode
  - token: sparse_window
    module: sparse_window
  - token: compute
    module: compute
  - token: mla
    module: compute
  - token: tail_policy
    module: tail_policy
  - token: search
    module: search
  - token: lowering
    module: lowering
```

- [ ] **Step 2: Write failing synthesizer test**

Create `tests/test_synthesizer.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import parse_stage1, EvidenceGraph
from stage2_synthesizer import synthesize


def test_synthesize_modules():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    outputs = synthesize(graph, output_dir=Path("/tmp/test_stage2_outputs"))
    assert "ontology" in outputs
    assert "modules.yaml" in outputs["ontology"]
```

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py::test_synthesize_modules -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'stage2_synthesizer'`

- [ ] **Step 3: Implement synthesizer — ontology generation**

Create `scripts/stage2_synthesizer.py`:
```python
#!/usr/bin/env python3
"""Synthesize Stage 2 artifacts from EvidenceGraph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from stage2_parser import EvidenceGraph, EvidenceNode


def _load_module_rules(rules_path: Path) -> dict[str, str]:
    raw = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    rules = {}
    for r in raw.get("rules", []):
        rules[r["token"]] = r["module"]
    rules["_fallback"] = raw.get("fallback", "needs_review")
    return rules


def _infer_module(field_path: str, rules: dict[str, str]) -> str:
    first_token = field_path.split(".")[0] if "." in field_path else field_path
    return rules.get(first_token, rules.get("_fallback", "needs_review"))


def _infer_field_type(meaning: str) -> str:
    m = meaning.lower()
    if any(w in m for w in ("coordinate", "key", "signature", "name", "path")):
        return "string"
    if any(w in m for w in ("formula", "sequence", "contract", "policy")):
        return "object"
    if any(w in m for w in ("size", "count", "number", "distance", "depth")):
        return "int"
    if any(w in m for w in ("enabled", "flag", "valid", "alias")):
        return "bool"
    if any(w in m for w in ("layout", "mode", "kind", "order")):
        return "enum"
    return "string"


def _infer_editable_policy(field_node: EvidenceNode, has_knob: bool) -> str:
    meaning = field_node.data.get("meaning", "").lower()
    if has_knob:
        return "searchable"
    if any(w in meaning for w in ("policy", "order", "mode", "layout")):
        return "configurable"
    if any(w in meaning for w in ("formula", "identity", "signature", "contract")):
        return "fixed"
    return "fixed"


def _ydump(obj: Any, indent: int = 0) -> str:
    sp = "  " * indent
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{sp}{k}:")
                lines.append(_ydump(v, indent + 1))
            else:
                lines.append(f"{sp}{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, str) else str(v).lower() if isinstance(v, bool) else v}")
        return "\n".join(lines)
    if isinstance(obj, list):
        lines = []
        for item in obj:
            if isinstance(item, dict):
                lines.append(f"{sp}-")
                lines.append(_ydump(item, indent + 1))
            else:
                lines.append(f"{sp}- {json.dumps(item, ensure_ascii=False) if isinstance(item, str) else item}")
        return "\n".join(lines)
    return f"{sp}{obj}"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


MANDATORY_VALIDATORS = [
    "ub_capacity",
    "l1_capacity",
    "workspace_no_alias",
    "sparse_window_alignment",
    "split_kv_lse_merge_valid",
    "event_dependency_valid",
    "l1_residency_loop_order",
]

MANDATORY_LOWERING = {
    "LowerTiling": (["tiling", "target", "features"], ["host_tiling_fields", "constexpr_constants"], ["host_tiling", "ComputeConstexpr"]),
    "LowerCoreMapping": (["core_mapping", "shape", "tiling"], ["logical_axis_mapping"], ["ComputeAxisIdx", "Process_loop_header"]),
    "LowerSparseWindow": (["sparse_window", "shape", "features"], ["s2_range_expressions"], ["GetS2LoopRange"]),
    "LowerL1Partition": (["l1_partition", "target", "decode", "tiling"], ["l1_regions", "TPipe_TBuf_allocation"], ["InitBuffer"]),
    "LowerL1Residency": (["l1_residency", "l1_partition", "decode.loop_order"], ["DataCopy_placement", "eviction_points"], ["Process", "LoadKvTile"]),
    "LowerDecodeLoopNest": (["decode", "core_mapping", "l1_residency"], ["kv_loops", "group_loops", "split_kv_loops"], ["Process"]),
    "LowerWorkspaceLayout": (["workspace", "decode.split_kv", "shape"], ["offset_functions", "partial_layout"], ["CalcWorkspaceOffset", "CalcAccumOffset"]),
    "LowerPipeline": (["pipeline", "memory", "compute"], ["stage_schedule", "event_variants"], ["Process", "pipeline_helpers"]),
}


def _build_canonical_optimizations(graph: EvidenceGraph) -> list[dict]:
    cards = [n for n in graph.nodes if n.kind == "card"]
    result = []
    for card in cards:
        modules = sorted(set(
            _infer_module(graph.get_node(e.to_id).data.get("path", ""), {"_fallback": "needs_review"})
            for e in graph.edges if e.from_id == card.id and e.label == "suggests"
            if graph.get_node(e.to_id) is not None
        ))
        if not modules:
            modules = ["tiling"]
        result.append({
            "id": card.id,
            "aliases": card.data.get("aliases", []),
            "intent": [card.data.get("optimization_intent", "")],
            "applies_to": card.data.get("applies_to", {}).get("variants", []),
            "preconditions": card.data.get("preconditions", []),
            "risks": card.data.get("risks", []),
            "required_dsl_modules": modules,
            "suggested_fields": [graph.get_node(e.to_id).data.get("path", "") for e in graph.edges if e.from_id == card.id and e.label == "suggests"],
            "searchable_knobs": card.data.get("tunable_knobs", []),
            "validators": [],
            "lowering_passes": [],
            "source_evidence": [e.to_id for e in graph.edges if e.from_id == card.id and e.label == "backed_by"],
        })
    return result


def _build_modules(canon: list[dict], graph: EvidenceGraph, rules: dict[str, str]) -> list[dict]:
    module_to_cards: dict[str, list[str]] = {}
    for item in canon:
        for m in item.get("required_dsl_modules", []):
            module_to_cards.setdefault(m, []).append(item["id"])

    # Collect fields per module
    module_fields: dict[str, list[tuple[str, dict]]] = {}
    for e in graph.edges:
        if e.label == "suggests":
            field_node = graph.get_node(e.to_id)
            if field_node and field_node.kind == "dsl_field":
                mod = _infer_module(field_node.data.get("path", ""), rules)
                module_fields.setdefault(mod, []).append((field_node.id, field_node.data))

    items = []
    for mod_name in sorted(module_to_cards.keys()):
        fields = module_fields.get(mod_name, [])
        searchable = []
        for field_id, field_data in fields:
            has_knob = any(
                ee.label == "tuned_by" and ee.from_id == field_id
                for ee in graph.edges
            )
            if has_knob:
                searchable.append(field_data.get("path", "").split(".")[-1])

        items.append({
            "name": mod_name,
            "responsibility": f"Generated from Stage 1 evidence for {mod_name}",
            "profile_scope": ["all"],
            "source_cards": sorted(set(module_to_cards.get(mod_name, []))),
            "core_fields": sorted(set(field_data.get("path", "").split(".")[-1] for _, field_data in fields)),
            "searchable_fields": sorted(set(searchable)),
            "hard_validators": [],
            "lowering_passes": [],
        })
    return items


def _build_field_policy(modules: list[dict]) -> dict[str, list[str]]:
    policies = {"searchable": [], "configurable": [], "fixed": [], "forbidden": []}
    for mod in modules:
        for f in mod.get("searchable_fields", []):
            policies["searchable"].append(f"{mod['name']}.{f}")
    return policies


def _build_module_schemas(graph: EvidenceGraph, rules: dict[str, str]) -> dict[str, dict]:
    schemas: dict[str, dict] = {}
    for e in graph.edges:
        if e.label == "suggests":
            field_node = graph.get_node(e.to_id)
            if not field_node or field_node.kind != "dsl_field":
                continue
            mod = _infer_module(field_node.data.get("path", ""), rules)
            schemas.setdefault(mod, {})

            field_path = field_node.data.get("path", "")
            field_name = field_path.split(".")[-1]
            meaning = field_node.data.get("meaning", "")
            confidence = field_node.data.get("confidence", "medium")

            has_knob = any(
                ee.label == "tuned_by" and ee.from_id == field_node.id
                for ee in graph.edges
            )

            # Collect source cards
            source_cards = sorted(set(
                ee.from_id for ee in graph.edges
                if ee.to_id == field_node.id and ee.label == "suggests"
            ))

            # Collect source evidence
            source_evidence = []
            for card_id in source_cards:
                for ee in graph.edges:
                    if ee.from_id == card_id and ee.label == "backed_by":
                        ev_node = graph.get_node(ee.to_id)
                        if ev_node and ev_node.kind == "evidence":
                            source_evidence.append(ev_node.id)
            source_evidence = sorted(set(source_evidence))

            schemas[mod][field_name] = {
                "type": _infer_field_type(meaning),
                "searchable": has_knob,
                "editable_policy": _infer_editable_policy(field_node, has_knob),
                "source_cards": source_cards,
                "source_evidence": source_evidence if source_evidence else ["needs_evidence: true"],
                "meaning": meaning,
                "confidence": confidence,
            }
    return schemas


def _build_validators(graph: EvidenceGraph) -> list[dict]:
    validators = []

    # Mandatory validators
    for v_name in MANDATORY_VALIDATORS:
        validators.append({
            "name": v_name,
            "module": "unknown",
            "severity": "hard",
            "inputs": [],
            "expr": "placeholder: needs derivation from evidence",
            "error_message": f"{v_name} failed",
            "related_risks": [],
            "source_cards": [],
            "source_evidence": ["needs_evidence: true"],
        })

    # Risk-derived validators
    for risk_node in graph.nodes:
        if risk_node.kind != "risk":
            continue
        risk_id = risk_node.id

        # Find forbidden transforms
        ft_ids = [e.to_id for e in graph.edges if e.from_id == risk_id and e.label == "forbids"]

        # Find constraints that also point to those FTs
        constraint_ids = []
        for ft_id in ft_ids:
            for e in graph.edges:
                if e.to_id == ft_id and e.label == "forbids" and e.from_id.startswith("C-"):
                    constraint_ids.append(e.from_id)

        # Find evidence backing
        evidence_ids = []
        for c_id in constraint_ids:
            c_node = graph.get_node(c_id)
            if c_node:
                for ev_id in c_node.data.get("source_evidence_ids", []):
                    evidence_ids.append(ev_id)

        v_name = f"valid_{risk_id.lower().replace('-', '_')}"
        validators.append({
            "name": v_name,
            "module": "derived",
            "severity": "hard",
            "inputs": constraint_ids,
            "expr": f"derived from {', '.join(constraint_ids) if constraint_ids else 'risk description'}",
            "error_message": f"{v_name} failed",
            "related_risks": [risk_id],
            "source_cards": [],
            "source_evidence": sorted(set(evidence_ids)) if evidence_ids else ["needs_evidence: true"],
        })

    return validators


def _build_lowering_specs(graph: EvidenceGraph) -> list[dict]:
    specs = []
    for name, (consumes, emits, patch_points) in MANDATORY_LOWERING.items():
        specs.append({
            "name": name,
            "consumes": consumes,
            "emits": emits,
            "patch_points": patch_points,
            "pre_validators": MANDATORY_VALIDATORS,
            "post_validators": ["compile_success", "golden_correctness"],
            "editable_policy": "limited_variants" if name == "LowerPipeline" else "template_or_patch_point",
            "source_cards": [],
        })
    return specs


def _build_shadow_dsl(graph: EvidenceGraph) -> dict[str, dict]:
    """Build shadow DSL per variant from high-confidence fields."""
    variants = {}
    for card_node in graph.nodes:
        if card_node.kind != "card":
            continue
        card_variants = card_node.data.get("applies_to", {}).get("variants", [])
        for variant in card_variants:
            if variant not in variants:
                variants[variant] = {"fields": []}

            # Collect high-confidence fields from this card
            for e in graph.edges:
                if e.from_id == card_node.id and e.label == "suggests":
                    field_node = graph.get_node(e.to_id)
                    if field_node and field_node.kind == "dsl_field":
                        if field_node.data.get("confidence", "medium") in ("high",):
                            variants[variant]["fields"].append({
                                "path": field_node.data.get("path", ""),
                                "meaning": field_node.data.get("meaning", ""),
                            })

    shadows = {}
    for variant, data in variants.items():
        shadows[variant] = {
            "version": "0.3",
            "kind": "ascend.attention.shadow",
            "variant": variant,
            "fields": data["fields"],
        }
    return shadows


def synthesize(graph: EvidenceGraph, output_dir: Path, rules_path: Path | None = None) -> dict[str, Any]:
    if rules_path is None:
        rules_path = Path(__file__).parent / "module_inference_rules.yaml"
    rules = _load_module_rules(rules_path)

    canon = _build_canonical_optimizations(graph)
    modules = _build_modules(canon, graph, rules)
    field_policy = _build_field_policy(modules)
    module_schemas = _build_module_schemas(graph, rules)
    validators = _build_validators(graph)
    lowering = _build_lowering_specs(graph)
    shadows = _build_shadow_dsl(graph)

    # Write ontology
    _write(output_dir / "ontology" / "canonical_optimizations.yaml", _ydump(canon))
    _write(output_dir / "ontology" / "modules.yaml", _ydump(modules))
    _write(output_dir / "ontology" / "field_policy.yaml", _ydump(field_policy))

    # Write schema
    _write(output_dir / "schema" / "atdsl.schema.yaml", _ydump({
        "version": "0.3",
        "kind": "ascend.attention.dsl_schema",
        "modules": [m["name"] for m in modules],
        "searchable_fields": field_policy.get("searchable", []),
        "readonly_fields": field_policy.get("fixed", []) + field_policy.get("forbidden", []),
        "validators": [v["name"] for v in validators],
        "lowering_passes": [s["name"] for s in lowering],
    }))

    for mod_name, fields in module_schemas.items():
        _write(output_dir / "schema" / "modules" / f"{mod_name}.schema.yaml", _ydump({mod_name: fields}))

    # Write validators
    for v in validators:
        _write(output_dir / "validators_spec" / f"{v['name']}.yaml", _ydump(v))

    # Write lowering
    for s in lowering:
        _write(output_dir / "lowering_spec" / f"{s['name']}.yaml", _ydump(s))

    # Write shadow examples
    for variant, shadow in shadows.items():
        _write(output_dir / "examples" / f"{variant}_shadow.yaml", _ydump(shadow))

    # Write review scaffold
    _write(output_dir / "review" / "schema_review.md", "# Stage 2 Schema Review\n\nGenerated by stage2_synthesizer.\n")
    _write(output_dir / "review" / "coverage_matrix.md", "# Stage 2 Coverage Matrix\n\nGenerated by stage2_synthesizer.\n")
    _write(output_dir / "review" / "missing_fields.md", "# Missing or Weak Fields\n\nGenerated by stage2_synthesizer.\n")

    return {
        "ontology": ["canonical_optimizations.yaml", "modules.yaml", "field_policy.yaml"],
        "schema": ["atdsl.schema.yaml"] + [f"{m}.schema.yaml" for m in module_schemas],
        "validators": [f"{v['name']}.yaml" for v in validators],
        "lowering": [f"{s['name']}.yaml" for s in lowering],
        "examples": [f"{v}_shadow.yaml" for v in shadows],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-graph", default="stage2_outputs/.evidence_graph.json")
    parser.add_argument("--output", default="stage2_outputs")
    parser.add_argument("--module-config", default=None)
    args = parser.parse_args()

    graph = EvidenceGraph.load(Path(args.evidence_graph))
    rules_path = Path(args.module_config) if args.module_config else None
    outputs = synthesize(graph, Path(args.output), rules_path)
    print(f"Synthesized {sum(len(v) for v in outputs.values())} files in {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run synthesizer test to verify it passes**

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py::test_synthesize_modules -v`

Expected: PASS

- [ ] **Step 5: Add more synthesizer tests**

Append to `tests/test_synthesizer.py`:
```python
def test_module_inference():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    outputs = synthesize(graph, output_dir=Path("/tmp/test_stage2_outputs_2"))

    # tiling.s1_base should map to tiling module
    schema_path = Path("/tmp/test_stage2_outputs_2/schema/modules/tiling.schema.yaml")
    assert schema_path.exists()
    content = schema_path.read_text()
    assert "s1_base" in content


def test_validator_generation():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    outputs = synthesize(graph, output_dir=Path("/tmp/test_stage2_outputs_3"))

    # Should have mandatory validators
    for v_name in ["ub_capacity", "l1_capacity", "workspace_no_alias"]:
        v_path = Path(f"/tmp/test_stage2_outputs_3/validators_spec/{v_name}.yaml")
        assert v_path.exists(), f"Missing validator {v_name}"

    # Should have risk-derived validator
    risk_v_path = Path("/tmp/test_stage2_outputs_3/validators_spec/valid_r_test_1.yaml")
    assert risk_v_path.exists()
```

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py -v`

Expected: all 3 tests PASS

- [ ] **Step 6: Commit synthesizer**

```bash
git add skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py \
        skills/stage2-dsl-ontology-builder/scripts/module_inference_rules.yaml \
        skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py
git commit -m "$(cat <<'EOF'
feat: Stage 2 Synthesizer with evidence-driven generation

- Infer modules from dsl_field.path tokens via configurable rules
- Generate schemas from card.possible_dsl_fields with type/policy inference
- Derive validators from risk->forbidden_transform->constraint chains
- Generate lowering specs from mandatory pass list + evidence trace
- Emit per-variant shadow DSL from high-confidence fields
- Unit tests verifying module inference, schema, validator generation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Verifier — Semantic Quality Gate

**Files:**
- Create: `skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py`
- Test: `skills/stage2-dsl-ontology-builder/tests/test_verifier.py`

- [ ] **Step 1: Write failing verifier test**

Create `tests/test_verifier.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import parse_stage1, EvidenceGraph
from stage2_synthesizer import synthesize
from stage2_verifier import verify


def test_verifier_runs():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify")
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)
    assert "overall_status" in result
```

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_verifier.py::test_verifier_runs -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'stage2_verifier'`

- [ ] **Step 2: Implement verifier**

Create `scripts/stage2_verifier.py`:
```python
#!/usr/bin/env python3
"""Semantic verifier for Stage 2 outputs against EvidenceGraph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from stage2_parser import EvidenceGraph, EvidenceNode


def _load_yaml_file(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _scan_placeholders(text: str) -> int:
    markers = ["needs evidence", "needs_evidence", "needs review", "placeholder"]
    return sum(text.lower().count(m) for m in markers)


def _check_evidence_connectivity(graph: EvidenceGraph) -> tuple[int, list[dict]]:
    score = 20
    issues = []

    for card_node in graph.nodes:
        if card_node.kind != "card":
            continue
        ev_edges = [e for e in graph.edges if e.from_id == card_node.id and e.label == "backed_by"]
        if not ev_edges:
            score -= 3
            issues.append({
                "severity": "error",
                "category": "evidence",
                "message": f"Card {card_node.id} has no evidence path",
                "remediation": "Add source_evidence entries or mark as needs_evidence: true",
            })

    for ev_node in graph.nodes:
        if ev_node.kind != "evidence":
            continue
        data = ev_node.data
        if not data.get("file") or not data.get("symbol"):
            score -= 2
            issues.append({
                "severity": "error",
                "category": "evidence",
                "message": f"Evidence {ev_node.id} missing file or symbol",
                "remediation": "Add file and symbol fields to source_evidence",
            })

    for node in graph.nodes:
        if node.kind != "dsl_field":
            continue
        card_edges = [e for e in graph.edges if e.to_id == node.id and e.label == "suggests"]
        if not card_edges:
            score -= 2
            issues.append({
                "severity": "warning",
                "category": "field",
                "message": f"Field {node.id} has no card source",
                "remediation": "Link field to at least one optimization card",
            })

    return max(0, score), issues


def _check_field_completeness(stage2_dir: Path, graph: EvidenceGraph) -> tuple[int, list[dict]]:
    score = 20
    issues = []
    placeholder_count = 0

    # Scan all schema files
    schema_dir = stage2_dir / "schema" / "modules"
    if schema_dir.exists():
        for fpath in schema_dir.rglob("*.yaml"):
            content = fpath.read_text(encoding="utf-8")
            placeholder_count += _scan_placeholders(content)

            data = yaml.safe_load(content)
            if not data:
                continue
            for mod_name, fields in data.items():
                if not isinstance(fields, dict):
                    continue
                for field_name, spec in fields.items():
                    if not isinstance(spec, dict):
                        continue
                    if "type" not in spec:
                        score -= 2
                        issues.append({
                            "severity": "error",
                            "category": "schema",
                            "message": f"Field {mod_name}.{field_name} missing type",
                        })
                    if "searchable" in spec and spec.get("searchable"):
                        if not any(k in spec for k in ("candidates", "range", "enum")):
                            score -= 3
                            issues.append({
                                "severity": "error",
                                "category": "schema",
                                "message": f"Searchable field {mod_name}.{field_name} has no candidates/range/enum",
                            })

    if placeholder_count > 20:
        score -= min(placeholder_count - 20, 8)
        issues.append({
            "severity": "warning",
            "category": "evidence",
            "message": f"Too many placeholder markers: {placeholder_count}",
        })

    return max(0, score), issues


def _check_knob_quality(graph: EvidenceGraph, stage2_dir: Path) -> tuple[int, list[dict]]:
    score = 15
    issues = []

    field_nodes = [n for n in graph.nodes if n.kind == "dsl_field"]
    for field_node in field_nodes:
        has_knob = any(
            e.label == "tuned_by" and e.from_id == field_node.id
            for e in graph.edges
        )
        if not has_knob:
            continue

        # Searchable field must map to a knob with domain
        knob_edges = [e for e in graph.edges if e.from_id == field_node.id and e.label == "tuned_by"]
        if not knob_edges:
            score -= 3
            issues.append({
                "severity": "error",
                "category": "knob",
                "message": f"Field {field_node.data.get('path')} searchable but no knob mapping",
            })
            continue

        knob_node = graph.get_node(knob_edges[0].to_id)
        if knob_node and "domain" in knob_node.data:
            domain = knob_node.data["domain"]
            if not any(k in domain for k in ("candidates", "range", "minimum", "maximum")):
                score -= 2
                issues.append({
                    "severity": "warning",
                    "category": "knob",
                    "message": f"Knob {knob_node.data.get('name')} domain not mapped to field range",
                })

    return max(0, score), issues


def _check_validator_coverage(graph: EvidenceGraph, stage2_dir: Path) -> tuple[int, list[dict]]:
    score = 20
    issues = []

    # Check mandatory validators exist
    mandatory = [
        "ub_capacity", "l1_capacity", "workspace_no_alias",
        "sparse_window_alignment", "split_kv_lse_merge_valid",
        "event_dependency_valid", "l1_residency_loop_order",
    ]
    for v_name in mandatory:
        v_path = stage2_dir / "validators_spec" / f"{v_name}.yaml"
        if not v_path.exists():
            score -= 5
            issues.append({
                "severity": "error",
                "category": "validator",
                "message": f"Missing mandatory validator: {v_name}",
            })

    # Check high-risk cards have validators
    for risk_node in graph.nodes:
        if risk_node.kind != "risk":
            continue
        risk_id = risk_node.id
        # Look for validator matching risk
        v_name = f"valid_{risk_id.lower().replace('-', '_')}"
        v_path = stage2_dir / "validators_spec" / f"{v_name}.yaml"
        if not v_path.exists():
            score -= 4
            issues.append({
                "severity": "error",
                "category": "validator",
                "message": f"High-risk card missing validator: {risk_id}",
            })

    # Check validator expr is not placeholder
    val_dir = stage2_dir / "validators_spec"
    if val_dir.exists():
        for vfile in val_dir.glob("*.yaml"):
            content = vfile.read_text()
            if "placeholder" in content.lower():
                score -= 2
                issues.append({
                    "severity": "warning",
                    "category": "validator",
                    "message": f"Validator {vfile.stem} has placeholder expr",
                })

    return max(0, score), issues


def _check_lowering_specs(stage2_dir: Path, graph: EvidenceGraph) -> tuple[int, list[dict]]:
    score = 10
    issues = []

    lowering_dir = stage2_dir / "lowering_spec"
    if not lowering_dir.exists():
        return 0, [{"severity": "error", "category": "lowering", "message": "No lowering_spec directory"}]

    for lfile in lowering_dir.glob("*.yaml"):
        data = _load_yaml_file(lfile)
        if not data:
            continue
        for key in ("consumes", "emits", "patch_points"):
            if key not in data or not data[key]:
                score -= 2
                issues.append({
                    "severity": "error",
                    "category": "lowering",
                    "message": f"Lowering pass {lfile.stem} missing {key}",
                })

    return max(0, score), issues


def _check_shadow_dsl_coverage(stage2_dir: Path, graph: EvidenceGraph) -> tuple[int, list[dict], dict]:
    score = 15
    issues = []
    coverage = {}

    # Count high-confidence fields per variant from graph
    variant_fields: dict[str, list[str]] = {}
    for card_node in graph.nodes:
        if card_node.kind != "card":
            continue
        variants = card_node.data.get("applies_to", {}).get("variants", [])
        for e in graph.edges:
            if e.from_id == card_node.id and e.label == "suggests":
                field_node = graph.get_node(e.to_id)
                if field_node and field_node.data.get("confidence") == "high":
                    for v in variants:
                        variant_fields.setdefault(v, []).append(field_node.data.get("path", ""))

    for variant, paths in variant_fields.items():
        total = len(set(paths))
        shadow_path = stage2_dir / "examples" / f"{variant}_shadow.yaml"
        covered = 0
        if shadow_path.exists():
            shadow_data = _load_yaml_file(shadow_path)
            if shadow_data:
                shadow_paths = {f.get("path", "") for f in shadow_data.get("fields", [])}
                covered = len(set(paths) & shadow_paths)

        pct = (covered / total * 100) if total > 0 else 0
        coverage[variant] = {"covered": covered, "total": total, "pct": round(pct, 1)}

        if pct < 60:
            variant_score = 0
        elif pct < 80:
            variant_score = (pct - 60) / 20 * (15 / len(variant_fields) if variant_fields else 15)
        else:
            variant_score = 15 / len(variant_fields) if variant_fields else 15

        score -= (15 / len(variant_fields) if variant_fields else 15) - variant_score

        if pct < 80:
            issues.append({
                "severity": "warning",
                "category": "shadow",
                "message": f"Shadow DSL coverage for {variant}: {pct:.1f}% (need >= 80%)",
                "remediation": f"Add {total - covered} missing fields to {variant}_shadow.yaml",
            })

    return max(0, round(score)), issues, coverage


def verify(graph: EvidenceGraph, stage2_dir: Path) -> dict[str, Any]:
    scores = {}
    all_issues = []

    scores["card_to_module_coverage"], issues = _check_evidence_connectivity(graph)
    all_issues.extend(issues)

    scores["field_design_completeness"], issues = _check_field_completeness(stage2_dir, graph)
    all_issues.extend(issues)

    scores["searchable_knob_quality"], issues = _check_knob_quality(graph, stage2_dir)
    all_issues.extend(issues)

    scores["validator_completeness"], issues = _check_validator_coverage(graph, stage2_dir)
    all_issues.extend(issues)

    scores["lowering_spec_clarity"], issues = _check_lowering_specs(stage2_dir, graph)
    all_issues.extend(issues)

    scores["shadow_dsl_coverage"], issues, coverage = _check_shadow_dsl_coverage(stage2_dir, graph)
    all_issues.extend(issues)

    total = sum(scores.values())
    hard_failures = [i for i in all_issues if i["severity"] == "error"]
    status = "pass" if total >= 85 and not hard_failures else "warn" if total >= 70 else "fail"

    result = {
        "overall_status": status,
        "total_score": total,
        "scores": scores,
        "hard_failures": [i["message"] for i in hard_failures],
        "semantic_issues": all_issues,
        "coverage": {"shadow_dsl": coverage},
        "next_actions": list(dict.fromkeys(
            i.get("remediation", f"Fix: {i['message']}") for i in all_issues
        )),
    }

    out = stage2_dir / "review" / "quality_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    # Also write markdown report
    md = ["# Stage 2 Quality Gate", "", f"Status: **{status}**", f"Total score: **{total}/100**", "", "## Scores", ""]
    for k, v in scores.items():
        md.append(f"- {k}: {v}")
    md += ["", "## Issues", ""]
    md += [f"- [{i['severity']}] ({i['category']}) {i['message']}" for i in all_issues] or ["- No issues found."]
    (stage2_dir / "review" / "quality_gate.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-graph", default="stage2_outputs/.evidence_graph.json")
    parser.add_argument("--stage2-dir", default="stage2_outputs")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    graph = EvidenceGraph.load(Path(args.evidence_graph))
    stage2_dir = Path(args.stage2_dir)
    result = verify(graph, stage2_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run verifier test**

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_verifier.py::test_verifier_runs -v`

Expected: PASS

- [ ] **Step 4: Add verifier score validation test**

Append to `tests/test_verifier.py`:
```python
def test_verifier_score_range():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_2")
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)
    assert 0 <= result["total_score"] <= 100
    assert result["overall_status"] in ("pass", "warn", "fail")
    assert "semantic_issues" in result


def test_verifier_mandatory_validators():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_3")
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)

    # With minimal fixtures, some mandatory validators won't have evidence
    # so score should be < 85 but >= 0
    assert result["total_score"] < 85  # because mandatory validators have placeholders
    assert result["overall_status"] == "warn" or result["overall_status"] == "fail"
```

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_verifier.py -v`

Expected: all 3 tests PASS

- [ ] **Step 5: Commit verifier**

```bash
git add skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py \
        skills/stage2-dsl-ontology-builder/tests/test_verifier.py
git commit -m "$(cat <<'EOF'
feat: Stage 2 Semantic Verifier with evidence-driven quality gate

- Evidence connectivity: cards->evidence paths, evidence completeness
- Field design completeness: type/meaning presence, searchable range check
- Knob quality: searchable field->knob domain mapping
- Validator coverage: mandatory validators + high-risk card validators
- Lowering spec clarity: consumes/emits/patch_points presence
- Shadow DSL coverage: per-variant coverage percentage calculation
- Output: quality_gate.json (superset of old format) + quality_gate.md
- Unit tests for score range, mandatory validator detection

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Integration Test Against Real Stage 1 Artifacts

**Files:**
- Create: `skills/stage2-dsl-ontology-builder/tests/test_integration.py`

- [ ] **Step 1: Write integration test**

Create `tests/test_integration.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import parse_stage1
from stage2_synthesizer import synthesize
from stage2_verifier import verify


def test_full_pipeline_on_real_data():
    """Run full pipeline against actual Stage 1 extraction."""
    input_dir = Path("artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction")
    if not input_dir.exists():
        pytest.skip("Real Stage 1 data not available")

    output_dir = Path("/tmp/test_stage2_integration")
    graph = parse_stage1(input_dir)
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    synthesize(graph, output_dir=output_dir)
    assert (output_dir / "ontology" / "canonical_optimizations.yaml").exists()
    assert (output_dir / "schema" / "atdsl.schema.yaml").exists()

    result = verify(graph, output_dir)
    assert result["total_score"] >= 0
    assert result["overall_status"] in ("pass", "warn", "fail")

    # Verify evidence graph is non-trivial
    card_count = len([n for n in graph.nodes if n.kind == "card"])
    assert card_count > 0
    print(f"Parsed {card_count} cards, {len(graph.nodes)} total nodes")
```

Run: `python -m pytest skills/stage2-dsl-ontology-builder/tests/test_integration.py -v -s`

Expected: PASS (if real data exists) or SKIP (if not)

- [ ] **Step 2: Commit integration test**

```bash
git add skills/stage2-dsl-ontology-builder/tests/test_integration.py
git commit -m "$(cat <<'EOF'
test: Integration test running full pipeline on real Stage 1 artifacts

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Update Documentation and Add Deprecation Shims

**Files:**
- Modify: `skills/stage2-dsl-ontology-builder/scripts/bootstrap_stage2.py`
- Modify: `skills/stage2-dsl-ontology-builder/scripts/check_stage2_quality.py`
- Modify: `skills/stage2-dsl-ontology-builder/SKILL.md`
- Modify: `skills/stage2-dsl-ontology-builder/README.md`
- Modify: `skills/stage2-dsl-ontology-builder/references/output_contract.md`
- Modify: `skills/stage2-dsl-ontology-builder/agents/openai.yaml`

- [ ] **Step 1: Add deprecation shim to bootstrap_stage2.py**

Read current `scripts/bootstrap_stage2.py`, then prepend deprecation header:

```python
#!/usr/bin/env python3
"""
DEPRECATED: This script is preserved for backward compatibility.
It now delegates to stage2_parser.py + stage2_synthesizer.py.
Use the new pipeline directly for evidence-driven generation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    print("WARNING: bootstrap_stage2.py is deprecated. Use stage2_parser.py + stage2_synthesizer.py instead.", file=sys.stderr)

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="stage1_outputs")
    parser.add_argument("--output", default="stage2_outputs")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    graph_path = output_dir / ".evidence_graph.json"

    # Run parser
    result = subprocess.run(
        [sys.executable, str(script_dir / "stage2_parser.py"), "--input", str(input_dir), "--output", str(graph_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Parser failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)

    # Run synthesizer
    result = subprocess.run(
        [sys.executable, str(script_dir / "stage2_synthesizer.py"), "--evidence-graph", str(graph_path), "--output", str(output_dir)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Synthesizer failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)

    print(f"Stage 2 scaffold created in {output_dir}")


if __name__ == "__main__":
    main()
```

Replace the entire content of `scripts/bootstrap_stage2.py` with the above.

- [ ] **Step 2: Add deprecation shim to check_stage2_quality.py**

Replace entire content of `scripts/check_stage2_quality.py` with:
```python
#!/usr/bin/env python3
"""
DEPRECATED: This script is preserved for backward compatibility.
It now delegates to stage2_verifier.py.
Use the new verifier directly for semantic quality checks.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    print("WARNING: check_stage2_quality.py is deprecated. Use stage2_verifier.py instead.", file=sys.stderr)

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="stage2_outputs")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    stage2_dir = Path(args.input)
    graph_path = stage2_dir / ".evidence_graph.json"

    result = subprocess.run(
        [sys.executable, str(script_dir / "stage2_verifier.py"), "--evidence-graph", str(graph_path), "--stage2-dir", str(stage2_dir)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update SKILL.md**

Replace the workflow section in `SKILL.md` (lines 101-115 approximately) with:
```markdown
## Workflow

### Step 0: Load references (unchanged)

Read these files as needed:
- `references/stage2_workflow.md`
- `references/output_contract.md`
- `references/schema_design_rules.md`
- `references/validators_and_lowering.md`
- `references/quality_gate.md`

### Step 1: Parse Stage 1 inputs into EvidenceGraph

```bash
python scripts/stage2_parser.py --input stage1_outputs --output stage2_outputs/.evidence_graph.json
```

This creates a typed graph of all cards, constraints, risks, evidence, knobs, pipeline nodes, and workspace regions with cross-reference edges.

### Step 2: Synthesize Stage 2 artifacts

```bash
python scripts/stage2_synthesizer.py --evidence-graph stage2_outputs/.evidence_graph.json --output stage2_outputs
```

This traverses the EvidenceGraph to infer modules, generate schemas, derive validators, and emit shadow DSL.

### Step 3: Run semantic quality gate

```bash
python scripts/stage2_verifier.py --evidence-graph stage2_outputs/.evidence_graph.json --stage2-dir stage2_outputs
```

This checks evidence connectivity, field completeness, knob mapping, validator coverage, lowering spec clarity, and shadow DSL coverage.

### Step 4: Manual refinement

The synthesizer generates evidence-driven scaffold. Codex should review:
- Fields marked `needs_evidence: true`
- Validators with placeholder `expr`
- Shadow DSL coverage gaps
- Module inference flagged as `needs_review`

Refine by updating Stage 1 artifacts and re-running the pipeline, or by editing `scripts/module_inference_rules.yaml`.

## Deprecated but preserved

```bash
python scripts/bootstrap_stage2.py --input stage1_outputs --output stage2_outputs  # delegates to parser + synthesizer
python scripts/check_stage2_quality.py --input stage2_outputs                     # delegates to verifier
```
```

Also update the `## Required output directory` section to mention `.evidence_graph.json`:
```markdown
## Required output directory

Default output directory: `stage2_outputs/`

In addition to the artifact directories, the pipeline produces:
- `stage2_outputs/.evidence_graph.json` — the typed EvidenceGraph intermediate representation.
```

- [ ] **Step 4: Update README.md**

Replace content with:
```markdown
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
```

- [ ] **Step 5: Update output_contract.md**

Append to `references/output_contract.md` after the existing quality_gate.json contract:
```markdown
## Extended quality_gate.json (v0.3)

The semantic verifier extends `quality_gate.json` with these additional fields:

```json
{
  "semantic_issues": [
    {
      "severity": "error|warning",
      "category": "evidence|schema|knob|validator|lowering|shadow",
      "message": "human-readable description",
      "remediation": "suggested fix"
    }
  ],
  "coverage": {
    "shadow_dsl": {
      "variant_name": {"covered": 8, "total": 12, "pct": 66.7}
    }
  },
  "next_actions": ["ordered list of fixes"]
}
```

All new fields are optional for backward compatibility. Consumers that only read `overall_status` and `scores` continue to work unchanged.
```

- [ ] **Step 6: Update agents/openai.yaml**

Replace with:
```yaml
name: stage2-dsl-ontology-builder
description: Build Stage 2 ATDSL ontology, schemas, validators, lowering specs, and shadow DSL examples from Stage 1 AscendC attention extraction artifacts.
recommended_model: gpt-5.5-thinking
inputs:
  - stage1_outputs
outputs:
  - stage2_outputs
  - stage2_outputs/.evidence_graph.json
agent_roles:
  - name: Parser Agent
    tool: scripts/stage2_parser.py
    input: stage1_outputs
    output: .evidence_graph.json
    purpose: Parse structured Stage 1 YAML into typed EvidenceGraph
  - name: Synthesizer Agent
    tool: scripts/stage2_synthesizer.py
    input: .evidence_graph.json
    output: stage2_outputs/*
    purpose: Generate ontology, schema, validators, lowering, and shadow DSL
  - name: Verifier Agent
    tool: scripts/stage2_verifier.py
    input: .evidence_graph.json + stage2_outputs
    output: review/quality_gate.json
    purpose: Semantic quality gate with evidence connectivity and coverage checks
```

- [ ] **Step 7: Commit documentation updates**

```bash
git add skills/stage2-dsl-ontology-builder/scripts/bootstrap_stage2.py \
        skills/stage2-dsl-ontology-builder/scripts/check_stage2_quality.py \
        skills/stage2-dsl-ontology-builder/SKILL.md \
        skills/stage2-dsl-ontology-builder/README.md \
        skills/stage2-dsl-ontology-builder/references/output_contract.md \
        skills/stage2-dsl-ontology-builder/agents/openai.yaml
git commit -m "$(cat <<'EOF'
docs: Update skill docs, add deprecation shims, document new pipeline

- bootstrap_stage2.py and check_stage2_quality.py now delegate to new pipeline
- SKILL.md updated with three-step workflow (parse -> synthesize -> verify)
- README.md quick-start uses new evidence-driven commands
- output_contract.md documents extended quality_gate.json format
- agents/openai.yaml defines Parser/Synthesizer/Verifier agent roles

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Final Integration Validation

**Files:**
- Run: all scripts against real data
- Verify: `review/quality_gate.json`

- [ ] **Step 1: Run full pipeline on real Stage 1 artifacts**

```bash
cd /mnt/workspace/xsearch_by_codex_app/xsearch
python skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py \
  --input artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction \
  --output /tmp/stage2_real/.evidence_graph.json

python skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py \
  --evidence-graph /tmp/stage2_real/.evidence_graph.json \
  --output /tmp/stage2_real

python skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py \
  --evidence-graph /tmp/stage2_real/.evidence_graph.json \
  --stage2-dir /tmp/stage2_real
```

Expected: All three scripts run without errors. Verifier prints a JSON result.

- [ ] **Step 2: Verify output structure matches contract**

```bash
ls /tmp/stage2_real/ontology/
ls /tmp/stage2_real/schema/modules/
ls /tmp/stage2_real/validators_spec/
ls /tmp/stage2_real/lowering_spec/
ls /tmp/stage2_real/examples/
cat /tmp/stage2_real/review/quality_gate.json | python -m json.tool
```

Expected: All required directories and files exist. quality_gate.json is valid JSON with `overall_status`, `scores`, and `semantic_issues`.

- [ ] **Step 3: Verify old shim still works**

```bash
python skills/stage2-dsl-ontology-builder/scripts/bootstrap_stage2.py \
  --input artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction \
  --output /tmp/stage2_shim

python skills/stage2-dsl-ontology-builder/scripts/check_stage2_quality.py \
  --input /tmp/stage2_shim
```

Expected: Both print deprecation warnings but complete successfully.

- [ ] **Step 4: Run all unit tests**

```bash
cd /mnt/workspace/xsearch_by_codex_app/xsearch
python -m pytest skills/stage2-dsl-ontology-builder/tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 5: Final commit**

```bash
git commit -m "$(cat <<'EOF'
feat: Stage 2 DSL Ontology Builder — evidence-driven three-layer pipeline

Complete replacement of hard-coded template generation with:
- stage2_parser.py: structured YAML -> EvidenceGraph JSON
- stage2_synthesizer.py: EvidenceGraph -> ontology/schema/validators/lowering/shadow
- stage2_verifier.py: semantic quality gate with 6 scoring dimensions
- module_inference_rules.yaml: configurable field-to-module mapping
- Full test coverage: unit + integration tests
- Backward compatible deprecation shims for old scripts
- Updated SKILL.md, README.md, output contract, agent definitions

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Plan Self-Review

### Spec Coverage

| Spec Section | Implementing Task(s) |
|---|---|
| Layer 1: EvidenceGraph Builder | Task 1 (parser + tests) |
| Layer 2: Synthesizer | Task 2 (synthesizer + module rules + tests) |
| Layer 3: Semantic Verifier | Task 3 (verifier + tests) |
| Module inference rules | Task 2 Step 1 |
| Incremental mode | Not in this plan (YAGNI — can be added later) |
| Shadow DSL per-variant | Task 2 Step 3 `_build_shadow_dsl` |
| Evidence connectivity check | Task 3 Step 2 `_check_evidence_connectivity` |
| Field completeness check | Task 3 Step 2 `_check_field_completeness` |
| Knob quality check | Task 3 Step 2 `_check_knob_quality` |
| Validator coverage check | Task 3 Step 2 `_check_validator_coverage` |
| Lowering spec clarity | Task 3 Step 2 `_check_lowering_specs` |
| Shadow DSL coverage | Task 3 Step 2 `_check_shadow_dsl_coverage` |
| quality_gate.json extended format | Task 3 Step 2 + Task 5 Step 5 |
| Agent workflow (Parser/Synthesizer/Verifier) | Task 5 Step 6 (agents/openai.yaml) |
| Deprecation shims | Task 5 Steps 1-2 |
| Updated docs | Task 5 Steps 3-5 |
| Integration test against real data | Task 4 + Task 6 |

**Gap identified: Incremental mode.** The spec mentions `--incremental` support but this plan does not implement it. This is intentional (YAGNI) — the default full-regeneration is fast enough for the current data size, and incremental mode can be added as a follow-up without breaking the API.

### Placeholder Scan

- No "TBD", "TODO", "implement later" found.
- No "add appropriate error handling" or "handle edge cases" found.
- Every test step shows actual test code.
- Every implementation step shows actual Python code.

### Type Consistency

- `EvidenceGraph`, `EvidenceNode`, `EvidenceEdge` defined in Task 1 and used consistently in Tasks 2-3.
- `parse_stage1()` signature: `(Path) -> EvidenceGraph` — consistent.
- `synthesize()` signature: `(EvidenceGraph, Path, Optional[Path]) -> dict` — consistent.
- `verify()` signature: `(EvidenceGraph, Path) -> dict` — consistent.
- quality_gate.json field names match between verifier output and output_contract.md.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-03-stage2-dsl-ontology-builder-improvement.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach?**
