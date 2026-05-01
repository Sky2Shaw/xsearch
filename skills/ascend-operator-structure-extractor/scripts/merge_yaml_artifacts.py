#!/usr/bin/env python3
"""Merge Ascend operator extraction YAML artifacts into a manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


AGGREGATE_FILES = {
    "cards/optimization_cards.yaml": "optimization_cards",
    "dsl/suggested_dsl_sections.yaml": "suggested_dsl_sections",
    "dsl/schema_gaps.yaml": "schema_gaps",
    "knobs/tunable_knobs.yaml": "tunable_knobs",
    "risks/risks.yaml": "risks",
    "constraints/constraints.yaml": "constraints",
}
MANIFEST_PATH = Path("reports/artifact_manifest.yaml")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge Ascend operator extraction YAML artifacts"
    )
    parser.add_argument("--output-root", required=True, help="Extraction output root")
    return parser.parse_args()


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return "''"
    if re.fullmatch(r"[A-Za-z0-9_./:+-]+", text) and text not in {"true", "false", "null"}:
        return text
    return json.dumps(text)


def to_yaml(value: Any, indent: int = 0) -> list[str]:
    space = " " * indent
    if isinstance(value, dict):
        if not value:
            return [space + "{}"]
        lines: list[str] = []
        for key, item in value.items():
            rendered_key = yaml_scalar(key)
            if isinstance(item, (dict, list)):
                lines.append(f"{space}{rendered_key}:")
                lines.extend(to_yaml(item, indent + 2))
            else:
                lines.append(f"{space}{rendered_key}: {yaml_scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [space + "[]"]
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{space}-")
                lines.extend(to_yaml(item, indent + 2))
            else:
                lines.append(f"{space}- {yaml_scalar(item)}")
        return lines
    return [space + yaml_scalar(value)]


def write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(to_yaml(value)) + "\n", encoding="utf-8")


def aggregate_placeholder_text(top_level_key: str) -> str:
    return "\n".join(to_yaml({top_level_key: []})) + "\n"


def validate_output_root(path_text: str) -> Path:
    output_root = Path(path_text).expanduser().resolve()
    if not output_root.exists():
        print(f"error: --output-root does not exist: {output_root}", file=sys.stderr)
        raise SystemExit(2)
    if not output_root.is_dir():
        print(f"error: --output-root must be a directory: {output_root}", file=sys.stderr)
        raise SystemExit(2)
    return output_root


def ensure_aggregate_files(output_root: Path) -> None:
    for relative_path, top_level_key in AGGREGATE_FILES.items():
        path = output_root / relative_path
        if not path.exists():
            write_yaml(path, {top_level_key: []})


def collect_yaml_artifacts(output_root: Path) -> list[str]:
    artifacts: list[str] = []
    aggregate_paths = {Path(path) for path in AGGREGATE_FILES}
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.suffix not in {".yaml", ".yml"}:
            continue
        relative_path = path.relative_to(output_root)
        if relative_path == MANIFEST_PATH:
            continue
        if relative_path in aggregate_paths:
            top_level_key = AGGREGATE_FILES[relative_path.as_posix()]
            if path.read_text(encoding="utf-8") == aggregate_placeholder_text(top_level_key):
                continue
        artifacts.append(relative_path.as_posix())
    return artifacts


def main() -> int:
    args = parse_args()
    output_root = validate_output_root(args.output_root)

    artifacts = collect_yaml_artifacts(output_root)
    ensure_aggregate_files(output_root)
    write_yaml(output_root / MANIFEST_PATH, {"artifact_manifest": artifacts})

    print(
        json.dumps(
            {
                "output_root": str(output_root),
                "yaml_artifacts": len(artifacts),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
