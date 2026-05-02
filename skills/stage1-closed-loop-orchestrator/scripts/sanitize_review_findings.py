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
    "target_files",
    "target_symbols",
    "required_artifacts",
    "required_evidence",
    "acceptance_checks",
    "evidence_class",
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    review_dir = Path(args.review_dir).expanduser().resolve()
    findings = collect_findings(review_dir)
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
