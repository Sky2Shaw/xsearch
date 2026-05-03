#!/usr/bin/env python3
"""Synthesize Stage 2 artifacts from EvidenceGraph."""

from __future__ import annotations

import argparse
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


def _write(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        content
        if isinstance(content, str)
        else yaml.safe_dump(content, sort_keys=False, allow_unicode=True)
    )
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


def _edges_from(graph: EvidenceGraph, node_id: str, label: str | None = None) -> list:
    return [
        edge for edge in graph.edges
        if edge.from_id == node_id and (label is None or edge.label == label)
    ]


def _edges_to(graph: EvidenceGraph, node_id: str, label: str | None = None) -> list:
    return [
        edge for edge in graph.edges
        if edge.to_id == node_id and (label is None or edge.label == label)
    ]


def _nodes_by_kind(graph: EvidenceGraph, kind: str) -> list[EvidenceNode]:
    return [node for node in graph.nodes if node.kind == kind]


def _field_path_for_node(node: EvidenceNode) -> str:
    return node.data.get("path") or node.data.get("field_path", "")


def _knob_for_field(graph: EvidenceGraph, field_id: str) -> EvidenceNode | None:
    for edge in _edges_from(graph, field_id, "tuned_by"):
        knob = graph.get_node(edge.to_id)
        if knob and knob.kind == "knob":
            return knob
    return None


def _finite_domain_from_knob(knob: EvidenceNode | None) -> dict | None:
    if knob is None:
        return None
    domain = knob.data.get("domain", {})
    if "candidates" in domain:
        return {"candidates": domain["candidates"]}
    if "values" in domain:
        return {"enum": domain["values"]}
    if "minimum" in domain and "maximum" in domain:
        range_spec = {
            "minimum": domain["minimum"],
            "maximum": domain["maximum"],
        }
        if "unit" in domain:
            range_spec["unit"] = domain["unit"]
        return {"range": range_spec}
    if "minimum" in domain:
        minimum = domain["minimum"]
        domain_spec = {"candidates": [minimum, minimum * 2, minimum * 4, minimum * 8]}
        if "unit" in domain:
            domain_spec["unit"] = domain["unit"]
        return domain_spec
    return {"kind": domain.get("kind", "unspecified")}


def _fixed_evidence_domain() -> dict[str, list[str]]:
    return {"enum": ["fixed_from_evidence"]}


def _agent_metadata_for_field(graph: EvidenceGraph, field_node: EvidenceNode) -> dict[str, Any]:
    ir_edges = _edges_from(graph, field_node.id, "field_maps_to_ir")
    ir_layer = "needs_review"
    schedule_points = []
    for edge in ir_edges:
        target = graph.get_node(edge.to_id)
        if target is None:
            continue
        if target.kind == "schedule_point":
            schedule_points.append(target.id)
        if "ir_layer" in target.data and target.data["ir_layer"] != "kernel":
            ir_layer = target.data["ir_layer"]
        elif target.id.startswith("ir:kernel:"):
            ir_layer = "kernel"

    feature_sources = [
        edge.from_id for edge in _edges_to(graph, field_node.id, "feature_derived_from")
    ]
    measurement_metrics = [
        edge.from_id.replace("metric:", "")
        for edge in _edges_to(graph, field_node.id, "metric_measures_field")
    ]

    return {
        "ir_layer": ir_layer,
        "schedule_points": sorted(set(schedule_points)),
        "feature_sources": sorted(set(feature_sources)),
        "measurement_metrics": sorted(set(measurement_metrics)),
        "replay_requirements": [
            "environment_fingerprint",
            "shape_signature",
            "dsl_version",
            "schedule_trace",
            "validator_results",
            "compile_result",
            "measurement_result",
            "failure_metadata",
        ],
    }


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
            knob_node = _knob_for_field(graph, field_node.id)
            agent_metadata = _agent_metadata_for_field(graph, field_node)

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

            field_spec = {
                "type": _infer_field_type(meaning),
                "searchable": has_knob,
                "editable_policy": _infer_editable_policy(field_node, has_knob),
                "source_cards": source_cards,
                "source_evidence": source_evidence if source_evidence else ["needs_evidence: true"],
                "meaning": meaning,
                "confidence": confidence,
                **agent_metadata,
            }
            if has_knob:
                finite_domain = _finite_domain_from_knob(knob_node)
                if finite_domain is not None:
                    field_spec.update(finite_domain)
            schemas[mod][field_name] = field_spec
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
            "expr": f"placeholder: derived from {', '.join(constraint_ids) if constraint_ids else 'risk description'}",
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
                    if field_node and field_node.data.get("confidence") == "high":
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


def _build_ir_artifacts(graph: EvidenceGraph) -> dict[str, dict]:
    semantic_entities = [
        node.data for node in _nodes_by_kind(graph, "semantic_entity")
        if node.data.get("ir_layer") == "semantic"
    ]
    kernel_schedule_points = [
        {
            "id": node.id,
            "field": node.data.get("field_path", ""),
            "action": node.data.get("action", ""),
            "searchable": node.data.get("searchable", False),
            "guard_validators": sorted(edge.to_id for edge in _edges_from(graph, node.id, "schedule_point_guarded_by")),
        }
        for node in _nodes_by_kind(graph, "schedule_point")
    ]
    capabilities = []
    for node in _nodes_by_kind(graph, "hardware_capability"):
        item = {"id": node.id, **node.data}
        item.setdefault("name", node.data.get("field_path", node.id))
        capabilities.append(item)
    metrics = [
        {"id": node.id, **node.data}
        for node in _nodes_by_kind(graph, "measurement_metric")
    ]
    features = [
        {"id": node.id, **node.data}
        for node in _nodes_by_kind(graph, "feature_source")
    ]
    tuning_record_fields = [
        {"id": node.id, **node.data}
        for node in _nodes_by_kind(graph, "tuning_record_field")
    ]

    return {
        "semantic_ir": {
            "version": "0.4",
            "kind": "ascend.attention.semantic_ir",
            "entities": semantic_entities,
        },
        "kernel_ir": {
            "version": "0.4",
            "kind": "ascend.attention.kernel_ir",
            "schedule_points": kernel_schedule_points,
        },
        "hardware_contract": {
            "version": "0.4",
            "kind": "ascend.attention.hardware_contract",
            "capabilities": capabilities,
        },
        "execution_feedback": {
            "version": "0.4",
            "kind": "ascend.attention.execution_feedback",
            "metrics": metrics,
            "features": features,
            "tuning_record_fields": tuning_record_fields,
        },
    }


def _build_search_artifacts(graph: EvidenceGraph) -> dict[str, dict]:
    schedule_points = []
    for node in _nodes_by_kind(graph, "schedule_point"):
        field_id = f"field:{node.data.get('field_path', '')}"
        field_node = graph.get_node(field_id)
        knob = _knob_for_field(graph, field_id)
        item = {
            "id": node.id,
            "field": node.data.get("field_path", ""),
            "action": node.data.get("action", ""),
            "searchable": node.data.get("searchable", False),
            "source_knob": knob.data.get("name") if knob else None,
            "guard_validators": sorted(edge.to_id for edge in _edges_from(graph, node.id, "schedule_point_guarded_by")),
            "forbidden_moves": ["event_wait_reorder", "online_softmax_formula_edit", "lse_formula_edit"],
        }
        finite_domain = _finite_domain_from_knob(knob)
        if finite_domain is not None:
            item.update(finite_domain)
        elif knob is None:
            item.update(_fixed_evidence_domain())
        if field_node is not None:
            item["meaning"] = field_node.data.get("meaning", "")
        schedule_points.append(item)

    return {
        "schedule_space": {
            "version": "0.4",
            "kind": "ascend.attention.schedule_space",
            "schedule_points": schedule_points,
        },
        "feature_schema": {
            "version": "0.4",
            "kind": "ascend.attention.feature_schema",
            "features": [{"id": node.id, **node.data} for node in _nodes_by_kind(graph, "feature_source")],
        },
        "measurement_schema": {
            "version": "0.4",
            "kind": "ascend.attention.measurement_schema",
            "metrics": [{"id": node.id, **node.data} for node in _nodes_by_kind(graph, "measurement_metric")],
        },
        "tuning_record_schema": {
            "version": "0.4",
            "kind": "ascend.attention.tuning_record_schema",
            "fields": [{"id": node.id, **node.data} for node in _nodes_by_kind(graph, "tuning_record_field")],
        },
    }


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
    ir_artifacts = _build_ir_artifacts(graph)
    search_artifacts = _build_search_artifacts(graph)

    # Write ontology
    _write(output_dir / "ontology" / "canonical_optimizations.yaml", canon)
    _write(output_dir / "ontology" / "modules.yaml", modules)
    _write(output_dir / "ontology" / "field_policy.yaml", field_policy)

    _write(output_dir / "ir" / "semantic_ir.yaml", ir_artifacts["semantic_ir"])
    _write(output_dir / "ir" / "kernel_ir.yaml", ir_artifacts["kernel_ir"])
    _write(output_dir / "ir" / "hardware_contract.yaml", ir_artifacts["hardware_contract"])
    _write(output_dir / "ir" / "execution_feedback.yaml", ir_artifacts["execution_feedback"])

    _write(output_dir / "search" / "schedule_space.yaml", search_artifacts["schedule_space"])
    _write(output_dir / "search" / "feature_schema.yaml", search_artifacts["feature_schema"])
    _write(output_dir / "search" / "measurement_schema.yaml", search_artifacts["measurement_schema"])
    _write(output_dir / "search" / "tuning_record.schema.yaml", search_artifacts["tuning_record_schema"])

    # Write schema
    _write(output_dir / "schema" / "atdsl.schema.yaml", {
        "version": "0.3",
        "kind": "ascend.attention.dsl_schema",
        "modules": [m["name"] for m in modules],
        "searchable_fields": field_policy.get("searchable", []),
        "readonly_fields": field_policy.get("fixed", []) + field_policy.get("forbidden", []),
        "validators": [v["name"] for v in validators],
        "lowering_passes": [s["name"] for s in lowering],
    })

    for mod_name, fields in module_schemas.items():
        _write(output_dir / "schema" / "modules" / f"{mod_name}.schema.yaml", {mod_name: fields})

    # Write validators
    for v in validators:
        _write(output_dir / "validators_spec" / f"{v['name']}.yaml", v)

    # Write lowering
    for s in lowering:
        _write(output_dir / "lowering_spec" / f"{s['name']}.yaml", s)

    # Write shadow examples
    for variant, shadow in shadows.items():
        _write(output_dir / "examples" / f"{variant}_shadow.yaml", shadow)

    # Write review scaffold
    _write(output_dir / "review" / "schema_review.md", "# Stage 2 Schema Review\n\nGenerated by stage2_synthesizer.\n")
    _write(output_dir / "review" / "coverage_matrix.md", "# Stage 2 Coverage Matrix\n\nGenerated by stage2_synthesizer.\n")
    _write(output_dir / "review" / "missing_fields.md", "# Missing or Weak Fields\n\nGenerated by stage2_synthesizer.\n")

    return {
        "ontology": ["canonical_optimizations.yaml", "modules.yaml", "field_policy.yaml"],
        "ir": ["semantic_ir.yaml", "kernel_ir.yaml", "hardware_contract.yaml", "execution_feedback.yaml"],
        "search": ["schedule_space.yaml", "feature_schema.yaml", "measurement_schema.yaml", "tuning_record.schema.yaml"],
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
