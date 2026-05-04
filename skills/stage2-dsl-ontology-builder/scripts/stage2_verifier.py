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
                        if not _has_finite_domain(spec):
                            score -= 3
                            issues.append({
                                "severity": "error",
                                "category": "schema",
                                "message": f"Searchable field {mod_name}.{field_name} has no finite candidates/range/enum",
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

    field_nodes = {
        n.data.get("path", ""): n
        for n in graph.nodes
        if n.kind == "dsl_field"
    }
    for field in _load_all_schema_fields(stage2_dir):
        spec = field["spec"]
        if not spec.get("searchable"):
            continue

        field_node = field_nodes.get(field["path"])
        if field_node is None:
            score -= 3
            issues.append({
                "severity": "error",
                "category": "knob",
                "message": f"Searchable field {field['path']} has no source DSL field",
            })
            continue

        knob_edges = [e for e in graph.edges if e.from_id == field_node.id and e.label == "tuned_by"]
        if not knob_edges:
            score -= 3
            issues.append({
                "severity": "error",
                "category": "knob",
                "message": f"Searchable field {field['path']} has no knob mapping",
            })
            continue

        knob_node = graph.get_node(knob_edges[0].to_id)
        if knob_node is None or "domain" not in knob_node.data:
            score -= 3
            issues.append({
                "severity": "error",
                "category": "knob",
                "message": f"Searchable field {field['path']} has no knob domain",
            })
            continue

        domain = knob_node.data["domain"]
        if not _has_finite_knob_domain(domain):
            score -= 2
            issues.append({
                "severity": "error",
                "category": "knob",
                "message": f"Knob {knob_node.data.get('name')} domain is not finite",
            })
            continue

        if not _knob_domain_maps_to_field(domain, spec):
            score -= 2
            issues.append({
                "severity": "error",
                "category": "knob",
                "message": f"Knob {knob_node.data.get('name')} domain is not mapped to searchable field {field['path']}",
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


def _load_all_schema_fields(stage2_dir: Path) -> list[dict[str, Any]]:
    fields = []
    schema_dir = stage2_dir / "schema" / "modules"
    if not schema_dir.exists():
        return fields
    for schema_file in schema_dir.glob("*.yaml"):
        data = _load_yaml_file(schema_file)
        if not isinstance(data, dict):
            continue
        for module_name, module_fields in data.items():
            if not isinstance(module_fields, dict):
                continue
            for field_name, spec in module_fields.items():
                if isinstance(spec, dict):
                    fields.append({
                        "module": module_name,
                        "name": field_name,
                        "path": f"{module_name}.{field_name}",
                        "spec": spec,
                    })
    return fields


def _agent_issue(severity: str, category: str, message: str, remediation: str) -> dict[str, str]:
    return {
        "severity": severity,
        "category": category,
        "message": message,
        "remediation": remediation,
    }


def _required_tuning_record_names(stage2_dir: Path) -> set[str]:
    path = stage2_dir / "search" / "tuning_record.schema.yaml"
    data = _load_yaml_file(path)
    if not isinstance(data, dict):
        return set()
    return {item.get("name", "") for item in data.get("fields", []) if isinstance(item, dict)}


def _has_finite_domain(data: dict[str, Any]) -> bool:
    if data.get("candidates") or data.get("enum"):
        return True
    domain_range = data.get("range")
    return isinstance(domain_range, dict) and "minimum" in domain_range and "maximum" in domain_range


def _has_finite_knob_domain(domain: dict[str, Any]) -> bool:
    if domain.get("candidates") or domain.get("values"):
        return True
    domain_range = domain.get("range")
    if isinstance(domain_range, dict):
        return "minimum" in domain_range and "maximum" in domain_range
    return "minimum" in domain


def _knob_domain_maps_to_field(domain: dict[str, Any], field_spec: dict[str, Any]) -> bool:
    if "candidates" in domain:
        expected = domain["candidates"]
        return field_spec.get("candidates") == expected or field_spec.get("enum") == expected
    if "values" in domain:
        expected = domain["values"]
        return field_spec.get("enum") == expected or field_spec.get("candidates") == expected

    domain_range = domain.get("range")
    if isinstance(domain_range, dict):
        field_range = field_spec.get("range")
        return (
            isinstance(field_range, dict)
            and field_range.get("minimum") == domain_range.get("minimum")
            and field_range.get("maximum") == domain_range.get("maximum")
        )

    if "minimum" in domain and "maximum" in domain:
        field_range = field_spec.get("range")
        return (
            isinstance(field_range, dict)
            and field_range.get("minimum") == domain.get("minimum")
            and field_range.get("maximum") == domain.get("maximum")
        )

    if "minimum" in domain:
        candidates = field_spec.get("candidates")
        return isinstance(candidates, list) and domain["minimum"] in candidates

    return False


def _check_agent_readiness(graph: EvidenceGraph, stage2_dir: Path) -> dict[str, Any]:
    scores = {
        "ir_layer_mapping": 20,
        "schedule_space_quality": 25,
        "hardware_contract_coverage": 20,
        "feedback_contract_completeness": 20,
        "replayability": 15,
    }
    issues: list[dict[str, str]] = []
    hard_failures: list[str] = []

    fields = _load_all_schema_fields(stage2_dir)
    schedule_data = _load_yaml_file(stage2_dir / "search" / "schedule_space.yaml") or {}
    hardware_data = _load_yaml_file(stage2_dir / "ir" / "hardware_contract.yaml") or {}
    feedback_data = _load_yaml_file(stage2_dir / "ir" / "execution_feedback.yaml") or {}

    schedule_points = schedule_data.get("schedule_points", []) if isinstance(schedule_data, dict) else []
    schedule_fields = {item.get("field") for item in schedule_points if isinstance(item, dict)}
    capability_names = {
        item.get("name")
        for item in hardware_data.get("capabilities", [])
        if isinstance(item, dict)
    } if isinstance(hardware_data, dict) else set()
    metrics = {
        item.get("name")
        for item in feedback_data.get("metrics", [])
        if isinstance(item, dict)
    } if isinstance(feedback_data, dict) else set()

    for field in fields:
        spec = field["spec"]
        if "ir_layer" not in spec or spec.get("ir_layer") == "needs_review":
            scores["ir_layer_mapping"] -= 3
            issues.append(_agent_issue(
                "warning", "ir",
                f"Field {field['path']} has no resolved IR layer",
                "Add an ir_layer mapping rule or mark the source field for review",
            ))

        if spec.get("searchable") and field["path"] not in schedule_fields:
            scores["schedule_space_quality"] -= 5
            message = f"Searchable field {field['path']} is missing from schedule_space"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Add the field to search/schedule_space.yaml"))

        if spec.get("searchable") and not _has_finite_domain(spec):
            scores["schedule_space_quality"] -= 5
            message = f"Searchable field {field['path']} has no range, candidates, or enum"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Map the source knob domain into the schema field"))

        if spec.get("ir_layer") == "hardware" and not capability_names:
            scores["hardware_contract_coverage"] -= 5
            message = f"Hardware field {field['path']} has no hardware contract"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "hardware", message, "Add a hardware capability entry"))

        lowered_path = field["path"].lower()
        if spec.get("searchable") and ("softmax" in lowered_path or "lse" in lowered_path or "formula" in lowered_path):
            scores["schedule_space_quality"] -= 8
            message = f"Unsafe formula field {field['path']} is searchable"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Mark formula fields fixed"))

    for item in schedule_points:
        if not isinstance(item, dict):
            continue
        if not item.get("guard_validators"):
            scores["schedule_space_quality"] -= 5
            message = f"Schedule point has no validator guard: {item.get('id', item.get('field', 'unknown'))}"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Attach at least one constraint, risk, or mandatory validator"))
        if item.get("searchable") and not _has_finite_domain(item):
            scores["schedule_space_quality"] -= 4
            message = f"Searchable schedule point has no domain: {item.get('id', item.get('field', 'unknown'))}"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Add range, candidates, or enum"))

    if not capability_names:
        scores["hardware_contract_coverage"] = 0
        hard_failures.append("Hardware contract has no capabilities")
        issues.append(_agent_issue("error", "hardware", "Hardware contract has no capabilities", "Generate ir/hardware_contract.yaml capabilities"))

    if not metrics:
        scores["feedback_contract_completeness"] = 0
        hard_failures.append("Execution feedback has no metrics")
        issues.append(_agent_issue("error", "feedback", "Execution feedback has no metrics", "Generate metrics in ir/execution_feedback.yaml"))

    required_record_fields = {
        "environment_fingerprint",
        "shape_signature",
        "dsl_version",
        "schedule_trace",
        "validator_results",
        "compile_result",
        "measurement_result",
        "failure_metadata",
    }
    missing_record_fields = required_record_fields - _required_tuning_record_names(stage2_dir)
    if missing_record_fields:
        scores["replayability"] -= min(15, len(missing_record_fields) * 3)
        message = f"Tuning record schema missing fields: {', '.join(sorted(missing_record_fields))}"
        hard_failures.append(message)
        issues.append(_agent_issue("error", "replay", message, "Add required replay fields to search/tuning_record.schema.yaml"))

    normalized_scores = {key: max(0, value) for key, value in scores.items()}
    total = sum(normalized_scores.values())
    status = "fail" if hard_failures else "pass" if total >= 85 else "warn" if total >= 70 else "fail"
    return {
        "status": status,
        "score": total,
        "scores": normalized_scores,
        "hard_failures": hard_failures,
        "issues": issues,
    }


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

    agent_readiness = _check_agent_readiness(graph, stage2_dir)

    total = sum(scores.values())
    hard_failures = [i for i in all_issues if i["severity"] == "error"]
    if hard_failures or agent_readiness["hard_failures"]:
        status = "fail"
    elif total >= 85 and agent_readiness["status"] != "fail":
        status = "pass"
    elif total >= 70:
        status = "warn"
    else:
        status = "fail"

    result = {
        "overall_status": status,
        "total_score": total,
        "scores": scores,
        "hard_failures": [i["message"] for i in hard_failures] + agent_readiness["hard_failures"],
        "semantic_issues": all_issues,
        "coverage": {"shadow_dsl": coverage},
        "agent_readiness": agent_readiness,
        "next_actions": list(dict.fromkeys(
            i.get("remediation", f"Fix: {i['message']}")
            for i in all_issues + agent_readiness["issues"]
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
    md += ["", "## Agent Readiness Issues", ""]
    md += [
        f"- [{i['severity']}] ({i['category']}) {i['message']}"
        for i in agent_readiness["issues"]
    ] or ["- No agent readiness issues found."]
    (stage2_dir / "review" / "quality_gate.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    readiness_md = ["# Stage 2 Agent Readiness", "", f"Status: **{agent_readiness['status']}**", f"Score: **{agent_readiness['score']}/100**", "", "## Scores", ""]
    for key, value in agent_readiness["scores"].items():
        readiness_md.append(f"- {key}: {value}")
    readiness_md += ["", "## Issues", ""]
    readiness_md += [
        f"- [{issue['severity']}] ({issue['category']}) {issue['message']}"
        for issue in agent_readiness["issues"]
    ] or ["- No issues found."]
    (stage2_dir / "review" / "agent_readiness.md").write_text("\n".join(readiness_md) + "\n", encoding="utf-8")

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
