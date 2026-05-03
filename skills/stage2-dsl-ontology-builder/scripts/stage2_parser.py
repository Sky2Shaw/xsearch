#!/usr/bin/env python3
"""Parse Stage 1 structured YAML into an EvidenceGraph."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
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
        path.parent.mkdir(parents=True, exist_ok=True)
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
    graphs = pipeline_data.get("pipeline_graphs", {})
    if not isinstance(graphs, dict):
        return
    for g in graphs.get("graphs", []):
        for node in g.get("nodes", []):
            node_id = node["id"]
            if graph.get_node(node_id) is None:
                graph.add_node(EvidenceNode(id=node_id, kind="pipeline_node", data=node))
            for ev_id in node.get("source_evidence_ids", []):
                graph.add_edge(EvidenceEdge(from_id=node_id, to_id=ev_id, label="backed_by"))


def _add_workspace_nodes(graph: EvidenceGraph, workspace_data: Any) -> None:
    layout = workspace_data.get("workspace_layout", {})
    if not isinstance(layout, dict):
        return
    for region in layout.get("regions", []):
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


def _resolve_file(input_dir: Path, *paths: str) -> Path:
    """Try nested path first, then flat path (for fixtures)."""
    nested = input_dir.joinpath(*paths)
    if nested.exists():
        return nested
    # Fallback: try basename only (flat fixtures directory)
    flat = input_dir / paths[-1]
    if flat.exists():
        return flat
    return nested  # return nested anyway so _load_yaml returns None gracefully


SEMANTIC_TOKENS = {"interface", "shape", "shape_layout", "layout", "compute", "features"}
KERNEL_TOKENS = {
    "tiling",
    "core_mapping",
    "memory",
    "l1_partition",
    "l1_residency",
    "workspace",
    "pipeline",
    "decode",
    "flash_decode",
    "sparse_window",
    "tail_policy",
}
HARDWARE_TOKENS = {"target"}
EXECUTION_TOKENS = {"search", "lowering"}

SCHEDULE_TOKENS = {
    "tiling",
    "core_mapping",
    "memory",
    "l1_partition",
    "l1_residency",
    "pipeline",
    "decode",
    "flash_decode",
    "sparse_window",
    "tail_policy",
}

CAPABILITY_BY_TOKEN = {
    "target": ["target_capability"],
    "memory": ["memory_space"],
    "l1_partition": ["l1_capacity"],
    "l1_residency": ["l1_capacity"],
    "workspace": ["workspace_capacity", "workspace_aliasing"],
    "sparse_window": ["alignment"],
}

DEFAULT_METRICS = [
    "latency_us",
    "throughput_ops",
    "bytes_global",
    "bytes_shared",
    "occupancy_estimate",
    "compile_time_ms",
    "correctness",
    "failure_code",
]

FEATURE_SOURCES = [
    "structural.loop_extents",
    "structural.reduction_depth",
    "memory.working_set",
    "memory.scope_reuse",
    "mapping.core_thread_mapping",
    "mapping.intrinsic_match",
    "history.similar_shape_key",
    "history.failure_category",
]

TUNING_RECORD_FIELDS = [
    "environment_fingerprint",
    "shape_signature",
    "dsl_version",
    "schedule_trace",
    "validator_results",
    "compile_result",
    "measurement_result",
    "failure_metadata",
]


def _add_node_once(graph: EvidenceGraph, node_id: str, kind: str, data: dict[str, Any]) -> None:
    if graph.get_node(node_id) is None:
        graph.add_node(EvidenceNode(id=node_id, kind=kind, data=data))


def _add_edge_once(graph: EvidenceGraph, from_id: str, to_id: str, label: str) -> None:
    if not any(e.from_id == from_id and e.to_id == to_id and e.label == label for e in graph.edges):
        graph.add_edge(EvidenceEdge(from_id=from_id, to_id=to_id, label=label))


def _first_path_token(field_path: str) -> str:
    return field_path.split(".")[0] if "." in field_path else field_path


def _infer_ir_layer(field_path: str, meaning: str) -> str:
    token = _first_path_token(field_path)
    lowered = meaning.lower()
    if token in SEMANTIC_TOKENS or any(word in lowered for word in ("formula", "identity", "tensor", "dtype", "layout")):
        return "semantic"
    if token in HARDWARE_TOKENS or any(word in lowered for word in ("capacity", "target", "ub", "l1")):
        return "hardware"
    if token in EXECUTION_TOKENS or any(word in lowered for word in ("metric", "trace", "record", "measure")):
        return "execution_feedback"
    if token in KERNEL_TOKENS:
        return "kernel"
    return "needs_review"


def _ir_node_kind(layer: str) -> str:
    if layer == "semantic":
        return "semantic_entity"
    if layer == "kernel":
        return "semantic_entity"
    if layer == "hardware":
        return "hardware_capability"
    if layer == "execution_feedback":
        return "tuning_record_field"
    return "semantic_entity"


def _schedule_point_for_field(field_path: str, has_knob: bool) -> str | None:
    token = _first_path_token(field_path)
    if token in SCHEDULE_TOKENS or has_knob:
        return f"schedule:{field_path}"
    return None


def _capabilities_for_field(field_path: str) -> list[str]:
    token = _first_path_token(field_path)
    capabilities = list(CAPABILITY_BY_TOKEN.get(token, []))
    lowered = field_path.lower()
    if "ub" in lowered and "ub_capacity" not in capabilities:
        capabilities.append("ub_capacity")
    if "l1" in lowered and "l1_capacity" not in capabilities:
        capabilities.append("l1_capacity")
    return sorted(set(capabilities))


def _source_cards_for_field(graph: EvidenceGraph, field_id: str) -> list[str]:
    return sorted({
        edge.from_id
        for edge in graph.edges
        if edge.to_id == field_id and edge.label == "suggests"
    })


def _guard_ids_for_field(graph: EvidenceGraph, field_id: str) -> list[str]:
    guards: set[str] = set()
    for card_id in _source_cards_for_field(graph, field_id):
        for edge in graph.edges:
            if edge.from_id == card_id and edge.label in {"constrained_by", "risked_by"}:
                guards.add(edge.to_id)
    for edge in graph.edges:
        if edge.from_id == field_id and edge.label == "tuned_by":
            knob_node = graph.get_node(edge.to_id)
            if knob_node:
                guards.update(knob_node.data.get("coupled_constraints", []))
    return sorted(guards)


def _add_agent_ready_nodes(graph: EvidenceGraph) -> None:
    field_nodes = [node for node in graph.nodes if node.kind == "dsl_field"]

    for field_node in field_nodes:
        field_path = field_node.data.get("path", "")
        meaning = field_node.data.get("meaning", "")
        has_knob = any(
            edge.from_id == field_node.id and edge.label == "tuned_by"
            for edge in graph.edges
        )
        layer = _infer_ir_layer(field_path, meaning)
        ir_node_id = f"ir:{layer}:{field_path}"
        _add_node_once(graph, ir_node_id, _ir_node_kind(layer), {
            "field_path": field_path,
            "ir_layer": layer,
            "meaning": meaning,
            "confidence": field_node.data.get("confidence", "medium"),
        })
        _add_edge_once(graph, field_node.id, ir_node_id, "field_maps_to_ir")

        schedule_id = _schedule_point_for_field(field_path, has_knob)
        if schedule_id:
            _add_node_once(graph, schedule_id, "schedule_point", {
                "field_path": field_path,
                "action": _first_path_token(field_path),
                "searchable": has_knob,
                "ir_layer": "kernel",
            })
            _add_edge_once(graph, field_node.id, schedule_id, "field_maps_to_ir")
            for guard_id in _guard_ids_for_field(graph, field_node.id):
                _add_edge_once(graph, schedule_id, guard_id, "schedule_point_guarded_by")

        for capability in _capabilities_for_field(field_path):
            capability_id = f"capability:{capability}"
            _add_node_once(graph, capability_id, "hardware_capability", {
                "name": capability,
                "source_field": field_path,
            })
            _add_edge_once(graph, field_node.id, capability_id, "field_requires_capability")

    for metric in DEFAULT_METRICS:
        metric_id = f"metric:{metric}"
        _add_node_once(graph, metric_id, "measurement_metric", {"name": metric})
        for field_node in field_nodes:
            _add_edge_once(graph, metric_id, field_node.id, "metric_measures_field")

    for feature in FEATURE_SOURCES:
        feature_id = f"feature:{feature}"
        _add_node_once(graph, feature_id, "feature_source", {"name": feature})
        for field_node in field_nodes:
            _add_edge_once(graph, feature_id, field_node.id, "feature_derived_from")

    for record_field in TUNING_RECORD_FIELDS:
        _add_node_once(graph, f"tuning_record:{record_field}", "tuning_record_field", {
            "name": record_field,
            "required": True,
        })


def parse_stage1(input_dir: Path) -> EvidenceGraph:
    graph = EvidenceGraph()

    files = {
        "cards": _resolve_file(input_dir, "cards", "optimization_cards.yaml"),
        "evidence": _resolve_file(input_dir, "evidence", "source_evidence.yaml"),
        "constraints": _resolve_file(input_dir, "constraints", "constraints.yaml"),
        "risks": _resolve_file(input_dir, "risks", "risks.yaml"),
        "knobs": _resolve_file(input_dir, "knobs", "tunable_knobs.yaml"),
        "pipeline": _resolve_file(input_dir, "auxiliary", "pipeline_graphs.yaml"),
        "workspace": _resolve_file(input_dir, "auxiliary", "workspace_layout.yaml"),
        "sections": _resolve_file(input_dir, "dsl", "suggested_dsl_sections.yaml"),
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
    _add_agent_ready_nodes(graph)

    return graph


def main() -> None:
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
