#!/usr/bin/env python3
"""Convert structured scorer outputs into a narrow re-extraction request."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SAFE_FINDING_KEYS = {
    "id",
    "severity",
    "dimension",
    "type",
    "priority",
    "target_files",
    "target_symbols",
    "required_artifacts",
    "required_evidence",
    "operator_info_needed",
    "score_impact",
    "expected_score_delta",
    "reextract_objective",
    "expected_artifact_updates",
    "acceptance_checks",
    "evidence_class",
}

DIMENSION_WEIGHTS = {
    "coverage": 25,
    "accuracy": 25,
    "traceability": 15,
    "dsl_convertibility": 20,
    "risks_constraints": 10,
    "dedup": 5,
}

DIMENSION_ALIASES = {
    "dsl-convertibility": "dsl_convertibility",
    "dsl convertibility": "dsl_convertibility",
    "risk_constraints": "risks_constraints",
    "risk & constraints": "risks_constraints",
    "risk_&_constraints": "risks_constraints",
    "risk_and_constraints": "risks_constraints",
    "risks and constraints": "risks_constraints",
    "risks_and_constraints": "risks_constraints",
    "risks_&_constraints": "risks_constraints",
    "dedup_canonicalization": "dedup",
    "dedup & canonicalization": "dedup",
    "dedup_&_canonicalization": "dedup",
    "dedup_and_canonicalization": "dedup",
}

SEVERITY_RANK = {
    "critical": 5,
    "blocking": 4,
    "major": 3,
    "minor": 2,
    "info": 1,
}

DEFAULT_OPERATOR_INFO_NEEDED = {
    "coverage": [
        "missing operator structures, critical functions, loop stages, memory "
        "hierarchy, pipeline stages, workspace layout, masks, and split-KV or "
        "merge behavior when present",
    ],
    "accuracy": [
        "source-backed file, function, line range, memory space, loop order, "
        "residency scope, synchronization, and dataflow facts for disputed claims",
    ],
    "traceability": [
        "source evidence entries with file, function, line_range, "
        "observed_behavior, and claim-to-source mapping",
    ],
    "dsl_convertibility": [
        "DSL module candidates, fields, enums, searchable knobs, validators, "
        "lowering hints, and forbidden transforms",
    ],
    "risks_constraints": [
        "hard constraints, correctness guards, forbidden transforms, overflow "
        "or aliasing risks, event hazards, alignment limits, and numerical "
        "stability constraints",
    ],
    "dedup": [
        "canonical names, aliases, duplicate pattern consolidation, and stable policy values",
    ],
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sanitize Stage 1 review findings")
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--previous-artifact-root", required=True)
    parser.add_argument("--output-artifact-root", required=True)
    return parser.parse_args(argv)


def read_json_yaml(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional(path: Path) -> Any:
    if not path.exists():
        return {}
    return read_json_yaml(path)


def write_json_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def refs_to_targets(refs: list[Any]) -> tuple[list[str], list[str]]:
    files: list[str] = []
    symbols: list[str] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        path = ref.get("path")
        function = ref.get("function")
        if isinstance(path, str) and path and path not in files:
            files.append(path)
        if isinstance(function, str) and function and function not in symbols:
            symbols.append(function)
    return files, symbols


def string_items(value: Any) -> list[str]:
    return [item for item in as_list(value) if isinstance(item, str) and item]


def unique_strings(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def normalize_dimension(value: Any) -> str:
    if not isinstance(value, str):
        return "review_finding"
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return DIMENSION_ALIASES.get(normalized, normalized)


def inferred_operator_info_needed(dimension: Any) -> list[str]:
    normalized = normalize_dimension(dimension)
    return DEFAULT_OPERATOR_INFO_NEEDED.get(
        normalized,
        [
            "specific operator facts needed to resolve this finding with source evidence",
        ],
    )


def sanitize_structured_finding(finding: dict[str, Any]) -> dict[str, Any]:
    sanitized = {key: finding[key] for key in SAFE_FINDING_KEYS if key in finding}
    refs = as_list(finding.get("source_or_artifact_ref"))
    files, symbols = refs_to_targets(refs)

    sanitized["target_files"] = string_items(sanitized.get("target_files")) + [
        item for item in files if item not in string_items(sanitized.get("target_files"))
    ]
    sanitized["target_symbols"] = string_items(sanitized.get("target_symbols")) + [
        item
        for item in symbols
        if item not in string_items(sanitized.get("target_symbols"))
    ]
    sanitized["required_artifacts"] = string_items(
        sanitized.get("required_artifacts")
    )
    sanitized["operator_info_needed"] = unique_strings(
        string_items(sanitized.get("operator_info_needed"))
        or inferred_operator_info_needed(sanitized.get("dimension"))
    )
    if "required_evidence" not in sanitized:
        sanitized["required_evidence"] = [
            "file",
            "function",
            "line_range",
            "observed_behavior",
        ]
    else:
        sanitized["required_evidence"] = string_items(
            sanitized.get("required_evidence")
        )
    if "acceptance_checks" not in sanitized:
        required_fix = finding.get("required_fix")
        sanitized["acceptance_checks"] = (
            [required_fix] if isinstance(required_fix, str) and required_fix else []
        )
    else:
        sanitized["acceptance_checks"] = string_items(
            sanitized.get("acceptance_checks")
        )
    if "type" not in sanitized:
        sanitized["type"] = sanitized.get("dimension", "review_finding")
    if "dimension" in sanitized:
        sanitized["dimension"] = normalize_dimension(sanitized["dimension"])
    return sanitized


def collect_findings(review_dir: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    blocking = load_optional(review_dir / "blocking_findings.yaml")
    blocking_items = (
        blocking.get("blocking_findings") if isinstance(blocking, dict) else blocking
    )
    for item in as_list(blocking_items):
        if isinstance(item, dict):
            findings.append(sanitize_structured_finding(item))

    missing = load_optional(review_dir / "missing_patterns.yaml")
    missing_items = (
        missing.get("missing_patterns") if isinstance(missing, dict) else missing
    )
    for item in as_list(missing_items):
        if isinstance(item, dict):
            findings.append(sanitize_structured_finding(item))
    return findings


def load_scorecard(review_dir: Path) -> dict[str, Any]:
    data = load_optional(review_dir / "scorecard.yaml")
    if not isinstance(data, dict):
        return {}
    scorecard = data.get("scorecard", data)
    return scorecard if isinstance(scorecard, dict) else {}


def numeric(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_dimension_scores(scorecard: dict[str, Any]) -> dict[str, dict[str, int]]:
    candidates: list[Any] = [
        scorecard.get("dimensions"),
        scorecard.get("score_breakdown"),
        scorecard.get("scores"),
        scorecard.get("score"),
        scorecard,
    ]
    scores: dict[str, dict[str, int]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for raw_dimension, raw_value in candidate.items():
            dimension = normalize_dimension(raw_dimension)
            if dimension == "total" or dimension not in DIMENSION_WEIGHTS:
                continue
            current: int | None = None
            maximum = DIMENSION_WEIGHTS[dimension]
            if isinstance(raw_value, dict):
                current = numeric(
                    raw_value.get("score", raw_value.get("current", raw_value.get("value")))
                )
                maximum = numeric(raw_value.get("max", raw_value.get("weight"))) or maximum
            else:
                current = numeric(raw_value)
            if current is not None and dimension not in scores:
                scores[dimension] = {"current": current, "max": maximum}
    return scores


def finding_score_gap(
    finding: dict[str, Any], dimension_scores: dict[str, dict[str, int]]
) -> int:
    dimension = normalize_dimension(finding.get("dimension"))
    score = dimension_scores.get(dimension)
    if not score:
        return 0
    return max(0, score["max"] - score["current"])


def severity_rank(finding: dict[str, Any]) -> int:
    severity = finding.get("severity")
    return SEVERITY_RANK.get(str(severity).lower(), 0)


def prioritize_findings(
    findings: list[dict[str, Any]], dimension_scores: dict[str, dict[str, int]]
) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda finding: (
            severity_rank(finding),
            finding_score_gap(finding, dimension_scores),
            str(finding.get("id", "")),
        ),
        reverse=True,
    )


def union_field(findings: list[dict[str, Any]], field: str) -> list[str]:
    values: list[str] = []
    for finding in findings:
        values.extend(string_items(finding.get(field)))
    return unique_strings(values)


def build_score_improvement_targets(
    findings: list[dict[str, Any]], dimension_scores: dict[str, dict[str, int]]
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        dimension = normalize_dimension(finding.get("dimension"))
        grouped.setdefault(dimension, []).append(finding)

    targets: list[dict[str, Any]] = []
    for dimension, dimension_findings in grouped.items():
        if dimension == "review_finding":
            continue
        target: dict[str, Any] = {
            "dimension": dimension,
            "related_finding_ids": [
                str(finding["id"])
                for finding in dimension_findings
                if isinstance(finding.get("id"), str) and finding["id"]
            ],
            "operator_info_needed": union_field(
                dimension_findings, "operator_info_needed"
            ),
            "target_files": union_field(dimension_findings, "target_files"),
            "target_symbols": union_field(dimension_findings, "target_symbols"),
            "required_artifacts": union_field(
                dimension_findings, "required_artifacts"
            ),
            "required_evidence": union_field(dimension_findings, "required_evidence"),
            "acceptance_checks": union_field(dimension_findings, "acceptance_checks"),
        }
        score = dimension_scores.get(dimension)
        if score:
            target["current_score"] = score["current"]
            target["max_score"] = score["max"]
            target["score_gap"] = max(0, score["max"] - score["current"])
        target["objective"] = (
            "Target only this scoring dimension's missing operator facts before broad regeneration."
        )
        targets.append(target)

    return sorted(
        targets,
        key=lambda target: (
            int(target.get("score_gap", 0)),
            len(target.get("related_finding_ids", [])),
            str(target.get("dimension", "")),
        ),
        reverse=True,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    review_dir = Path(args.review_dir).expanduser().resolve()
    scorecard = load_scorecard(review_dir)
    dimension_scores = extract_dimension_scores(scorecard)
    findings = prioritize_findings(collect_findings(review_dir), dimension_scores)
    if not findings:
        print(f"error: no structured review findings found in {review_dir}", file=sys.stderr)
        return 2

    request = {
        "reextraction_request": {
            "run_id": args.run_id,
            "round": args.round,
            "source_root": args.source_root,
            "previous_artifact_root": args.previous_artifact_root,
            "output_artifact_root": args.output_artifact_root,
            "required_fixes": findings,
            "score_improvement_targets": build_score_improvement_targets(
                findings, dimension_scores
            ),
            "forbidden_context": [
                "extractor_conversation",
                "scorer_reasoning_trace",
                "full_score_report",
            ],
        }
    }
    output = Path(args.output).expanduser().resolve()
    write_json_yaml(output, request)
    print(json.dumps({"output": str(output), "required_fix_count": len(findings)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
