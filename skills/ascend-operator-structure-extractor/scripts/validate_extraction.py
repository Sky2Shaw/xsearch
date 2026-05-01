#!/usr/bin/env python3
"""Validate Ascend operator extraction artifact structure."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - depends on caller environment.
    yaml = None


REQUIRED_DIRS = [
    "reports",
    "annotations/functions/index",
    "annotations/functions/brief",
    "annotations/functions/deep",
    "annotations/files",
    "cards",
    "dsl",
    "knobs",
    "constraints",
    "risks",
    "learning",
]

REQUIRED_REPORTS = {
    "reports/repo_map.yaml": "repo_map",
    "reports/file_inventory.yaml": "file_inventory",
    "reports/function_index.yaml": "function_index",
    "reports/function_importance.yaml": "function_importance",
    "reports/skipped_or_shallow_items.yaml": "skipped_or_shallow_items",
}

STANDARD_ARTIFACT_KEYS = {
    "reports/artifact_manifest.yaml": "artifact_manifest",
    "reports/operator_structure_report.yaml": "analysis_result",
    "cards/optimization_cards.yaml": "optimization_cards",
    "dsl/suggested_dsl_sections.yaml": "suggested_dsl_sections",
    "dsl/schema_gaps.yaml": "schema_gaps",
    "knobs/tunable_knobs.yaml": "tunable_knobs",
    "constraints/constraints.yaml": "constraints",
    "risks/risks.yaml": "risks",
    "learning/learned_patterns.yaml": "learned_patterns",
    "learning/checklist_updates.yaml": "checklist_updates",
    "learning/negative_lessons.yaml": "negative_lessons",
    "learning/evolution_patch.yaml": "evolution_result",
}
CRITICAL_STAGE_FUNCTIONS = {
    "ComputeMm1",
    "ComputeMm2",
    "ProcessMm1",
    "ProcessMm2",
    "IterateBmm1",
    "IterateBmm2",
    "ComputeBmm1",
    "ComputeBmm2",
}

TOP_LEVEL_KEY_PATTERN = re.compile(
    r'^(?:"([^"]+)"|\'([^\']+)\'|([A-Za-z_][A-Za-z0-9_-]*)):(?:\s|$)'
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Ascend operator extraction artifacts"
    )
    parser.add_argument("--output-root", required=True, help="Extraction output root")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero when warnings are present",
    )
    return parser.parse_args()


def validate_output_root(path_text: str) -> tuple[Path, list[str]]:
    output_root = Path(path_text).expanduser().resolve()
    errors: list[str] = []
    if not output_root.exists():
        errors.append(f"--output-root does not exist: {output_root}")
    elif not output_root.is_dir():
        errors.append(f"--output-root must be a directory: {output_root}")
    return output_root, errors


def read_text(path: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{path} is not valid UTF-8 text")
    except OSError as exc:
        errors.append(f"could not read {path}: {exc}")
    return None


def top_level_keys(text: str) -> list[str]:
    keys: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1].isspace():
            continue
        match = TOP_LEVEL_KEY_PATTERN.match(line)
        if match:
            keys.append(next(group for group in match.groups() if group is not None))
    return keys


def has_key_like_yaml_structure(text: str) -> bool:
    return bool(top_level_keys(text))


def has_unterminated_quote(line: str) -> bool:
    in_single = False
    in_double = False
    index = 0
    while index < len(line):
        char = line[index]
        if char == "#" and not in_single and not in_double:
            break
        if char == "'" and not in_double:
            if in_single and index + 1 < len(line) and line[index + 1] == "'":
                index += 2
                continue
            in_single = not in_single
        elif char == '"' and not in_single:
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                in_double = not in_double
        index += 1
    return in_single or in_double


def flow_delimiter_error(text: str) -> str | None:
    stack: list[tuple[str, int]] = []
    in_single = False
    in_double = False
    line_number = 1
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\n":
            line_number += 1
            index += 1
            continue
        if char == "#" and not in_single and not in_double:
            while index < len(text) and text[index] != "\n":
                index += 1
            continue
        if char == "'" and not in_double:
            if in_single and index + 1 < len(text) and text[index + 1] == "'":
                index += 2
                continue
            in_single = not in_single
        elif char == '"' and not in_single:
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and text[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                in_double = not in_double
        elif not in_single and not in_double:
            if char in "[{":
                stack.append((char, line_number))
            elif char in "]}":
                if not stack:
                    return f"unmatched {char!r} on line {line_number}"
                opener, opener_line = stack.pop()
                if (opener, char) not in {("[", "]"), ("{", "}")}:
                    return (
                        f"mismatched {opener!r} on line {opener_line} "
                        f"closed by {char!r} on line {line_number}"
                    )
        index += 1
    if stack:
        opener, opener_line = stack[-1]
        return f"unmatched {opener!r} on line {opener_line}"
    return None


def fallback_validate_yaml_text(path: Path, text: str, expected_key: str | None, errors: list[str]) -> bool:
    if not text.strip():
        errors.append(f"{path} is empty")
        return False
    if "\t" in text:
        errors.append(f"{path} contains tab characters")
        return False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if has_unterminated_quote(line):
            errors.append(f"{path}:{line_number} has an unterminated quoted scalar")
            return False
    delimiter_error = flow_delimiter_error(text)
    if delimiter_error is not None:
        errors.append(f"{path} has malformed flow delimiters: {delimiter_error}")
        return False
    keys = top_level_keys(text)
    if not keys:
        errors.append(f"{path} does not look like key-based YAML")
        return False
    if expected_key is not None and keys[0] != expected_key:
        errors.append(f"{path} first top-level key must be {expected_key}")
        return False
    return True


def validate_loaded_yaml(
    path: Path,
    loaded: Any,
    expected_key: str | None,
    errors: list[str],
) -> bool:
    if loaded is None:
        errors.append(f"{path} is empty")
        return False
    if not isinstance(loaded, dict):
        errors.append(f"{path} must contain a top-level mapping")
        return False
    if expected_key is None:
        if not loaded:
            errors.append(f"{path} does not contain any top-level keys")
            return False
        return True
    if expected_key not in loaded:
        errors.append(f"{path} is missing expected top-level key: {expected_key}")
        return False
    value = loaded[expected_key]
    if expected_key == "repo_map":
        if not isinstance(value, dict):
            errors.append(f"{path} top-level repo_map value must be a mapping")
            return False
    elif not isinstance(value, (dict, list)):
        errors.append(f"{path} top-level {expected_key} value must be a mapping or list")
        return False
    return True


def validate_yaml_file(path: Path, expected_key: str | None, errors: list[str]) -> bool:
    text = read_text(path, errors)
    if text is None:
        return False
    if yaml is not None:
        try:
            loaded = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            errors.append(f"{path} is malformed YAML: {exc}")
            return False
        return validate_loaded_yaml(path, loaded, expected_key, errors)
    return fallback_validate_yaml_text(path, text, expected_key, errors)


def load_yaml_file(path: Path, warnings: list[str]) -> Any | None:
    if yaml is None:
        warnings.append("PyYAML is unavailable; semantic coverage validation is skipped")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        warnings.append(f"could not load {path} for semantic validation: {exc}")
        return None


def normalize_identity(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    normalized = re.sub(r"\s+", "", text)
    result: list[str] = []
    depth = 0
    for char in normalized:
        if char == "<":
            depth += 1
            continue
        if char == ">" and depth:
            depth -= 1
            continue
        if depth == 0:
            result.append(char)
    return "".join(result)


def function_name_from_identity(text: Any) -> str:
    normalized = normalize_identity(text)
    if "::" in normalized:
        return normalized.rsplit("::", 1)[-1]
    return normalized


def function_index_entries(output_root: Path, warnings: list[str]) -> list[dict[str, Any]]:
    path = output_root / "reports/function_index.yaml"
    if not path.exists():
        return []
    loaded = load_yaml_file(path, warnings)
    if not isinstance(loaded, dict):
        return []
    functions = loaded.get("function_index", {}).get("functions", [])
    return [item for item in functions if isinstance(item, dict)]


def deep_annotation_entries(output_root: Path, warnings: list[str]) -> list[dict[str, Any]]:
    deep_dir = output_root / "annotations/functions/deep"
    if not deep_dir.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(deep_dir.glob("*.y*ml")):
        loaded = load_yaml_file(path, warnings)
        if not isinstance(loaded, dict):
            continue
        value = loaded.get("function_annotation")
        if isinstance(value, list):
            entries.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            entries.append(value)
    return entries


def semantic_names(entry: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("canonical_name", "qualified_name", "function_name"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            names.add(normalize_identity(value))
    return names


def validate_required_dirs(output_root: Path, errors: list[str]) -> None:
    for relative_dir in REQUIRED_DIRS:
        path = output_root / relative_dir
        if not path.exists():
            errors.append(f"missing required directory: {relative_dir}")
        elif not path.is_dir():
            errors.append(f"required path is not a directory: {relative_dir}")


def validate_required_reports(output_root: Path, errors: list[str]) -> None:
    for relative_path, expected_key in REQUIRED_REPORTS.items():
        path = output_root / relative_path
        if not path.exists():
            errors.append(f"missing required report: {relative_path}")
            continue
        if not path.is_file():
            errors.append(f"required report is not a file: {relative_path}")
            continue
        validate_yaml_file(path, expected_key, errors)


def validate_function_indexes(output_root: Path, warnings: list[str]) -> None:
    index_dir = output_root / "annotations/functions/index"
    if index_dir.is_dir() and not any(index_dir.glob("*.yml")) and not any(index_dir.glob("*.yaml")):
        warnings.append("no per-function index YAML files found under annotations/functions/index")
    functions = function_index_entries(output_root, warnings)
    if not functions:
        return

    functions_by_file_name: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for function in functions:
        file = str(function.get("file", ""))
        name = str(function.get("function_name", ""))
        functions_by_file_name.setdefault((file, name), []).append(function)

    for function in functions:
        file = str(function.get("file", ""))
        name = str(function.get("function_name", ""))
        if name not in CRITICAL_STAGE_FUNCTIONS or "op_kernel" not in file:
            continue
        if function.get("extraction_level") != "deep":
            warnings.append(
                "critical stage function is not marked deep: "
                f"{file}:{function.get('line_range', {}).get('start', '?')}:{name} "
                f"(level={function.get('extraction_level')})"
            )
        qualified = function.get("qualified_name")
        canonical = function.get("canonical_name")
        owner = function.get("owner") or function.get("owner_qualified")
        if (not canonical and qualified == name) or not owner:
            warnings.append(
                "critical stage function lacks template/owner identity: "
                f"{file}:{function.get('line_range', {}).get('start', '?')}:{name}"
            )

    for function in functions:
        file = str(function.get("file", ""))
        calls = function.get("calls", [])
        if not isinstance(calls, list):
            continue
        for call in calls:
            if call in CRITICAL_STAGE_FUNCTIONS and (file, call) not in functions_by_file_name:
                warnings.append(
                    "possible function-boundary parse gap: "
                    f"{file}:{function.get('function_name')} calls {call}, "
                    "but no same-file function index entry exists"
                )


def validate_deep_stage_coverage(output_root: Path, warnings: list[str]) -> None:
    deep_entries = deep_annotation_entries(output_root, warnings)
    if not deep_entries:
        return
    deep_names = set().union(*(semantic_names(entry) for entry in deep_entries))

    file_dir = output_root / "annotations/files"
    if not file_dir.is_dir():
        return
    for path in sorted(file_dir.glob("*.y*ml")):
        loaded = load_yaml_file(path, warnings)
        if not isinstance(loaded, dict):
            continue
        analysis = loaded.get("file_analysis")
        if not isinstance(analysis, dict):
            continue
        important = analysis.get("important_functions", [])
        if not isinstance(important, list):
            continue
        for item in important:
            if not isinstance(item, dict):
                continue
            qualified_name = item.get("qualified_name")
            function_name = function_name_from_identity(qualified_name)
            if function_name not in CRITICAL_STAGE_FUNCTIONS:
                continue
            normalized = normalize_identity(qualified_name)
            if normalized and normalized not in deep_names:
                warnings.append(
                    "important critical-stage function is absent from deep annotations: "
                    f"{qualified_name} referenced by {path.relative_to(output_root)}"
                )


def validate_operator_report(output_root: Path, errors: list[str], warnings: list[str]) -> None:
    path = output_root / "reports/operator_structure_report.yaml"
    if not path.exists():
        warnings.append("reports/operator_structure_report.yaml is absent; expected before aggregation")
        return
    if not path.is_file():
        errors.append("reports/operator_structure_report.yaml exists but is not a file")
        return
    validate_yaml_file(path, "analysis_result", errors)


def expected_key_for_artifact(output_root: Path, path: Path) -> str | None:
    relative = path.relative_to(output_root).as_posix()
    if relative in REQUIRED_REPORTS:
        return REQUIRED_REPORTS[relative]
    if relative in STANDARD_ARTIFACT_KEYS:
        return STANDARD_ARTIFACT_KEYS[relative]

    parts = relative.split("/")
    if len(parts) >= 4 and parts[:3] == ["annotations", "functions", "index"]:
        return "function_index_entry"
    if len(parts) >= 4 and parts[:3] == ["annotations", "functions", "brief"]:
        return "function_brief"
    if len(parts) >= 4 and parts[:3] == ["annotations", "functions", "deep"]:
        return "function_annotation"
    if len(parts) >= 3 and parts[:2] == ["annotations", "files"]:
        return "file_analysis"
    if len(parts) >= 2 and parts[0] == "cards":
        return "optimization_cards"
    if len(parts) >= 2 and parts[0] == "dsl":
        if path.name == "schema_gaps.yaml":
            return "schema_gaps"
        return "suggested_dsl_sections"
    if len(parts) >= 2 and parts[0] == "knobs":
        return "tunable_knobs"
    if len(parts) >= 2 and parts[0] == "constraints":
        return "constraints"
    if len(parts) >= 2 and parts[0] == "risks":
        return "risks"
    if len(parts) >= 2 and parts[0] == "learning":
        return None
    return None


def validate_all_yaml_artifacts(output_root: Path, errors: list[str]) -> None:
    checked: set[Path] = set()
    for relative_path in REQUIRED_REPORTS:
        checked.add(output_root / relative_path)
    checked.add(output_root / "reports/operator_structure_report.yaml")

    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path.suffix not in {".yaml", ".yml"}:
            continue
        if path in checked and path.exists():
            continue
        expected_key = expected_key_for_artifact(output_root, path)
        validate_yaml_file(path, expected_key, errors)


def main() -> int:
    args = parse_args()
    output_root, errors = validate_output_root(args.output_root)
    warnings: list[str] = []

    if not errors:
        validate_required_dirs(output_root, errors)
        validate_required_reports(output_root, errors)
        validate_function_indexes(output_root, warnings)
        validate_operator_report(output_root, errors, warnings)
        validate_all_yaml_artifacts(output_root, errors)
        validate_deep_stage_coverage(output_root, warnings)

    result = {
        "output_root": str(output_root),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, indent=2))

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
