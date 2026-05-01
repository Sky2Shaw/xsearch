#!/usr/bin/env python3
"""Prepare source-aware review context for Stage-1 extraction artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


IMPORTANT_FILES = {
    "function_index": "reports/function_index.yaml",
    "function_importance": "reports/function_importance.yaml",
    "critical_path": "reports/critical_path_annotations.yaml",
    "operator_report": "reports/operator_structure_report.yaml",
    "optimization_cards": "cards/optimization_cards.yaml",
    "suggested_dsl_sections": "dsl/suggested_dsl_sections.yaml",
    "schema_gaps": "dsl/schema_gaps.yaml",
    "tunable_knobs": "knobs/tunable_knobs.yaml",
    "constraints": "constraints/constraints.yaml",
    "risks": "risks/risks.yaml",
}

REQUIRED_CRITICAL_ITEMS = {
    "gqa.mm1": ["gqa", "mm1"],
    "gqa.vec1": ["gqa", "vec1"],
    "gqa.mm2": ["gqa", "mm2", "ComputeMm2"],
    "gqa.vec2.output": ["gqa", "vec2"],
    "mla.mm1": ["mla", "mm1"],
    "mla.vec1": ["mla", "vec1"],
    "mla.mm2": ["mla", "mm2", "ComputeMm2"],
    "mla.mm2.process": ["mla", "ProcessMm2"],
    "mla.vec2.output": ["mla", "vec2"],
    "mla.nupdate.compute": ["mla", "nupdate"],
    "mla.nupdate.apply": ["mla", "ProcessAmlaNupdate"],
    "flash_decode.merge": ["flash_decode", "FlashDecode"],
    "generic.mm2": ["nonquant", "ComputeMm2"],
}

TEMPLATE_FIELDS = [
    "canonical_name",
    "owner",
    "owner_qualified",
    "owner_template_args",
    "template_params",
    "variant",
    "stage",
]

CRITICAL_STAGE_ALIASES: Dict[str, List[str]] = {
    "gqa.vec1": ["gqa.vec1.output"],
    "mla.vec1": ["mla.vec1.output"],
}

KNOWN_CRITICAL_STAGE_NAMES = set(REQUIRED_CRITICAL_ITEMS)
for _aliases in CRITICAL_STAGE_ALIASES.values():
    KNOWN_CRITICAL_STAGE_NAMES.update(_aliases)


_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or line[i - 1].isspace():
                return line[:i].rstrip()
    return line.rstrip()


def _yaml_lines(text: str) -> List[Tuple[int, str]]:
    lines: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        cleaned = _strip_comment(raw)
        if not cleaned.strip():
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        lines.append((indent, cleaned.strip()))

    merged: List[Tuple[int, str]] = []
    for indent, stripped in lines:
        key_like = False
        if ":" in stripped and not stripped.startswith("- "):
            key = stripped.split(":", 1)[0].strip()
            key_like = bool(_KEY_RE.match(key))
        if merged and not stripped.startswith("- ") and not key_like:
            previous_indent, previous = merged[-1]
            merged[-1] = (previous_indent, f"{previous} {stripped}")
        else:
            merged.append((indent, stripped))
    return merged


def _split_key_value(text: str, require_key: bool = True) -> Optional[Tuple[str, str]]:
    if ":" not in text:
        return None
    key, value = text.split(":", 1)
    key = key.strip()
    if require_key and not _KEY_RE.match(key):
        return None
    return key, value.strip()


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _split_inline_items(value: str) -> List[str]:
    items: List[str] = []
    current: List[str] = []
    depth = 0
    quote: Optional[str] = None
    for ch in value:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in {"'", '"'}:
            quote = ch
            current.append(ch)
        elif ch in "[{":
            depth += 1
            current.append(ch)
        elif ch in "]}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current or value.strip():
        items.append("".join(current).strip())
    return items


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in _split_inline_items(inner)]
    if value.startswith("{") and value.endswith("}"):
        inner = value[1:-1].strip()
        result: Dict[str, Any] = {}
        if not inner:
            return result
        for item in _split_inline_items(inner):
            pair = _split_key_value(item, require_key=False)
            if pair is None:
                return _unquote(value)
            key, raw = pair
            result[_unquote(key.strip())] = _parse_scalar(raw)
        return result
    if re.fullmatch(r"[-+]?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass
    if re.fullmatch(r"[-+]?\d+\.\d+", value):
        try:
            return float(value)
        except ValueError:
            pass
    return _unquote(value)


def _parse_yaml_block(lines: List[Tuple[int, str]], index: int, indent: int) -> Tuple[Any, int]:
    if index >= len(lines):
        return {}, index

    current_indent, current_text = lines[index]
    if current_indent < indent:
        return {}, index

    if current_text.startswith("- ") and current_indent == indent:
        result: List[Any] = []
        while index < len(lines):
            line_indent, text = lines[index]
            if line_indent != indent or not text.startswith("- "):
                break
            item_text = text[2:].strip()
            index += 1

            if not item_text:
                child, index = _parse_yaml_block(lines, index, indent + 2)
                result.append(child)
                continue

            pair = _split_key_value(item_text)
            if pair is None:
                result.append(_parse_scalar(item_text))
                continue

            key, raw = pair
            item: Dict[str, Any] = {}
            if raw:
                item[key] = _parse_scalar(raw)
            else:
                child_indent = _child_indent(lines, index, indent)
                child, index = _parse_yaml_block(lines, index, child_indent)
                item[key] = child

            while index < len(lines):
                next_indent, next_text = lines[index]
                if next_indent <= indent:
                    break
                if next_indent == indent + 2 and not next_text.startswith("- "):
                    next_pair = _split_key_value(next_text)
                    if next_pair is None:
                        break
                    next_key, next_raw = next_pair
                    index += 1
                    if next_raw:
                        item[next_key] = _parse_scalar(next_raw)
                    else:
                        child_indent = _child_indent(lines, index, next_indent)
                        child, index = _parse_yaml_block(lines, index, child_indent)
                        item[next_key] = child
                else:
                    break
            result.append(item)
        return result, index

    result: Dict[str, Any] = {}
    while index < len(lines):
        line_indent, text = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            break
        if text.startswith("- "):
            break
        pair = _split_key_value(text)
        if pair is None:
            raise ValueError(f"cannot parse line: {text}")
        key, raw = pair
        index += 1
        if raw:
            result[key] = _parse_scalar(raw)
        else:
            child_indent = _child_indent(lines, index, line_indent)
            child, index = _parse_yaml_block(lines, index, child_indent)
            result[key] = child
    return result, index


def _child_indent(lines: List[Tuple[int, str]], index: int, parent_indent: int) -> int:
    if index >= len(lines):
        return parent_indent + 2
    next_indent, next_text = lines[index]
    if next_text.startswith("- ") and next_indent >= parent_indent:
        return next_indent
    if next_indent > parent_indent:
        return next_indent
    return parent_indent + 2


def _fallback_yaml_load(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return {}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    lines = _yaml_lines(text)
    if not lines:
        return {}
    parsed, index = _parse_yaml_block(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError("unparsed trailing YAML lines")
    return parsed


def read_json_compatible_yaml(path: Path) -> Any:
    text = read_text(path)
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        return {} if loaded is None else loaded
    except Exception as exc:
        yaml_error = str(exc)

    try:
        return _fallback_yaml_load(text)
    except Exception as exc:
        return {
            "_parse_status": "text_fallback",
            "_parse_error": str(exc),
            "_yaml_error": yaml_error,
            "_text": text,
        }


def dump_json_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _nested(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _load_if_exists(input_dir: Path, relative: str) -> Any:
    path = input_dir / relative
    if not path.exists():
        return None
    return read_json_compatible_yaml(path)


def _parse_status(data: Any) -> str:
    if isinstance(data, dict) and data.get("_parse_status") == "text_fallback":
        return "text_fallback"
    return "parsed"


def _count_named_list(data: Any, key: str, path_exists: bool) -> int:
    if isinstance(data, dict):
        value = data.get(key)
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict):
            for nested_value in value.values():
                if isinstance(nested_value, list):
                    return len(nested_value)
    if isinstance(data, list):
        return len(data)
    return 1 if path_exists else 0


def _function_index_functions(data: Any) -> List[Dict[str, Any]]:
    candidates = [
        _nested(data, "function_index", "functions"),
        _nested(data, "functions"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def _critical_path_stages(data: Any) -> List[Dict[str, Any]]:
    candidates = [
        _nested(data, "critical_path_annotations", "stages"),
        _nested(data, "critical_path", "stages"),
        _nested(data, "stages"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def _optimization_cards(data: Any) -> List[Dict[str, Any]]:
    candidates = [
        _nested(data, "optimization_cards"),
        _nested(data, "optimization_card"),
        data,
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict) and candidate is not data:
            return [candidate]
    return []


def _dsl_sections(data: Any) -> List[Dict[str, Any]]:
    candidates = [
        _nested(data, "suggested_dsl_sections"),
        _nested(data, "dsl_sections"),
        _nested(data, "sections"),
        data,
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def collect_inventory(input_dir: Path) -> Dict[str, Any]:
    important_files: Dict[str, Any] = {}
    parse_errors: Dict[str, str] = {}
    parsed: Dict[str, Any] = {}

    for name, relative in IMPORTANT_FILES.items():
        path = input_dir / relative
        metadata = {
            "path": relative,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        if path.exists():
            data = read_json_compatible_yaml(path)
            parsed[name] = data
            metadata["parse_status"] = _parse_status(data)
            if metadata["parse_status"] != "parsed":
                parse_errors[relative] = data.get("_parse_error", "parse failed") if isinstance(data, dict) else "parse failed"
        important_files[name] = metadata

    counts = {
        "indexed_functions": len(_function_index_functions(parsed.get("function_index"))),
        "brief_annotations": len(list((input_dir / "annotations" / "functions" / "brief").glob("*.yaml"))),
        "deep_annotations": len(list((input_dir / "annotations" / "functions" / "deep").glob("*.yaml"))),
        "index_annotations": len(list((input_dir / "annotations" / "functions" / "index").glob("*.yaml"))),
        "file_annotations": len(list((input_dir / "annotations" / "files").glob("*.yaml"))),
        "optimization_cards": _count_named_list(parsed.get("optimization_cards"), "optimization_cards", important_files["optimization_cards"]["exists"]),
        "tunable_knobs": _count_named_list(parsed.get("tunable_knobs"), "tunable_knobs", important_files["tunable_knobs"]["exists"]),
        "constraints": _count_named_list(parsed.get("constraints"), "constraints", important_files["constraints"]["exists"]),
        "risks": _count_named_list(parsed.get("risks"), "risks", important_files["risks"]["exists"]),
        "dsl_sections": _count_named_list(parsed.get("suggested_dsl_sections"), "suggested_dsl_sections", important_files["suggested_dsl_sections"]["exists"]),
        "schema_gaps": _count_named_list(parsed.get("schema_gaps"), "schema_gaps", important_files["schema_gaps"]["exists"]),
    }

    return {
        "input_dir": str(input_dir),
        "important_files": important_files,
        "counts": counts,
        "parse_errors": parse_errors,
    }


def _sanitize_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return sanitized


def _file_exists(input_dir: Path, relative: Optional[str]) -> bool:
    return bool(relative) and (input_dir / relative).exists()


def _resolve_relative_path(input_dir: Path, relative: Optional[str]) -> Optional[str]:
    if not relative:
        return None
    exact = input_dir / relative
    if exact.exists():
        return relative
    parent = exact.parent
    if parent.exists():
        basename = exact.name
        for candidate in sorted(parent.glob(f"*{basename}")):
            if candidate.is_file():
                return str(candidate.relative_to(input_dir))
    return relative


def _line_range(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    return value


def _non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _template_identity_complete(function: Dict[str, Any]) -> bool:
    return all(_non_empty(function.get(field)) for field in TEMPLATE_FIELDS)


def _annotation_from_stage(stage: Dict[str, Any], level: str) -> Optional[str]:
    preferred = f"{level}_annotation"
    if isinstance(stage.get(preferred), str):
        return stage[preferred]
    for key in ("deep_annotation", "brief_annotation", "index_annotation", "annotation"):
        if isinstance(stage.get(key), str):
            return stage[key]
    return None


def _annotation_by_sanitized(input_dir: Path, canonical_name: str, level: str) -> Optional[str]:
    candidate = f"annotations/functions/{level}/{_sanitize_name(canonical_name)}.yaml"
    resolved = _resolve_relative_path(input_dir, candidate)
    return resolved if resolved and (input_dir / resolved).exists() else None


def _stage_metadata(stage: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in stage.items() if k not in {"deep_annotation", "brief_annotation", "index_annotation"}}


def build_cross_reference(input_dir: Path, parsed: Dict[str, Any], inventory: Dict[str, Any]) -> Dict[str, Any]:
    functions = _function_index_functions(parsed.get("function_index"))
    stages = _critical_path_stages(parsed.get("critical_path"))
    stage_by_function: Dict[str, Dict[str, Any]] = {}
    critical_stage_to_function: Dict[str, Any] = {}

    for stage in stages:
        canonical = str(stage.get("canonical_name", "")).strip()
        stage_name = str(stage.get("stage", "")).strip()
        annotation_path = _resolve_relative_path(input_dir, _annotation_from_stage(stage, "deep"))
        if canonical:
            stage_by_function[canonical] = stage
        if stage_name:
            critical_stage_to_function[stage_name] = {
                "canonical_name": canonical,
                "deep_annotation": annotation_path,
                "present": bool(canonical),
                "variant": stage.get("variant"),
                "annotation_path": annotation_path,
                "annotation_exists": _file_exists(input_dir, annotation_path),
                "metadata": _stage_metadata(stage),
            }

    function_to_annotation: Dict[str, Any] = {}
    for function in functions:
        canonical = str(function.get("canonical_name", "")).strip()
        if not canonical:
            continue
        level = str(function.get("extraction_level") or "index").strip().lower()
        if level not in {"deep", "brief", "index"}:
            level = "index"
        stage = stage_by_function.get(canonical, {})
        annotation_path = _resolve_relative_path(input_dir, _annotation_from_stage(stage, level))
        annotation_path = annotation_path or _annotation_by_sanitized(input_dir, canonical, level)
        if annotation_path is None and level != "index":
            annotation_path = _annotation_by_sanitized(input_dir, canonical, "index")
        annotation_exists = _file_exists(input_dir, annotation_path)
        reported_level = level if annotation_path else "missing"
        missing_template_fields = [field for field in TEMPLATE_FIELDS if not _non_empty(function.get(field))]

        function_to_annotation[canonical] = {
            "level": reported_level,
            "annotation_path": annotation_path,
            "function_index_path": IMPORTANT_FILES["function_index"],
            "annotation_exists": annotation_exists,
            "critical_stage": stage.get("stage"),
            "file": function.get("file"),
            "stage": function.get("stage"),
            "variant": function.get("variant"),
            "line_range": _line_range(function.get("line_range")),
            "template_identity_complete": _template_identity_complete(function),
            "missing_template_fields": missing_template_fields,
            "template_identity_missing_fields": missing_template_fields,
        }

    cards_to_evidence: List[Dict[str, Any]] = []
    for index, card in enumerate(_optimization_cards(parsed.get("optimization_cards")), start=1):
        key = str(card.get("id") or card.get("canonical_name") or card.get("title") or f"card_{index}")
        evidence = card.get("evidence", card.get("source_evidence", []))
        evidence_items = _as_list(evidence)
        cards_to_evidence.append({
            "id": key,
            "title": card.get("title"),
            "evidence_count": len(evidence_items),
            "evidence": _as_list(evidence),
            "confidence": card.get("confidence"),
        })

    dsl_sections_to_evidence: List[Dict[str, Any]] = []
    for index, section in enumerate(_dsl_sections(parsed.get("suggested_dsl_sections")), start=1):
        key = str(section.get("name") or section.get("path") or section.get("id") or f"dsl_section_{index}")
        evidence: List[Any] = []
        if "evidence" in section:
            evidence.extend(_as_list(section.get("evidence")))
        fields = _as_list(section.get("fields"))
        for field in fields:
            if isinstance(field, dict) and "evidence" in field:
                evidence.extend(_as_list(field.get("evidence")))
        dsl_sections_to_evidence.append({
            "name": key,
            "field_count": len(fields),
            "evidence_count": len(evidence),
            "evidence": evidence,
            "fields": fields,
        })

    return {
        "function_to_annotation": function_to_annotation,
        "critical_stage_to_function": critical_stage_to_function,
        "cards_to_evidence": cards_to_evidence,
        "dsl_sections_to_evidence": dsl_sections_to_evidence,
    }


def _critical_identity_text(stage_name: str, canonical_name: str, stage_data: Dict[str, Any], function_data: Optional[Dict[str, Any]]) -> str:
    metadata = stage_data.get("metadata", {}) if isinstance(stage_data.get("metadata"), dict) else {}
    identity_parts: List[Any] = [
        stage_name,
        canonical_name,
        stage_data.get("variant"),
        metadata.get("stage"),
        metadata.get("canonical_name"),
        metadata.get("variant"),
        metadata.get("owner"),
        metadata.get("owner_qualified"),
        metadata.get("owner_template_args"),
    ]
    if isinstance(function_data, dict):
        identity_parts.extend(
            [
                function_data.get("canonical_name"),
                function_data.get("function_name"),
                function_data.get("qualified_name"),
                function_data.get("variant"),
                function_data.get("stage"),
                function_data.get("owner"),
                function_data.get("owner_qualified"),
                function_data.get("owner_template_args"),
            ]
        )
    return " ".join(json.dumps(part, ensure_ascii=False) if isinstance(part, (list, dict)) else str(part) for part in identity_parts if part).lower()


def _identity_matches_required_item(
    item: str,
    tokens: List[str],
    stage_name: str,
    canonical_name: str,
    stage_data: Dict[str, Any],
    function_data: Optional[Dict[str, Any]],
) -> bool:
    identity_text = _critical_identity_text(stage_name, canonical_name, stage_data, function_data)
    return all(token.lower() in identity_text for token in tokens)


def _is_known_critical_stage(stage_name: str) -> bool:
    return bool(stage_name) and stage_name in KNOWN_CRITICAL_STAGE_NAMES


def _critical_stage_evidence(stage_data: Dict[str, Any]) -> List[Any]:
    evidence: List[Any] = []
    for key in ("deep_annotation", "annotation_path"):
        value = stage_data.get(key)
        if value and value not in evidence:
            evidence.append(value)
    metadata = stage_data.get("metadata", {}) if isinstance(stage_data.get("metadata"), dict) else {}
    for key in ("file", "line_range"):
        value = metadata.get(key)
        if value and value not in evidence:
            evidence.append(value)
    return evidence


def _critical_match(stage_name: str, canonical_name: str, stage_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "stage": stage_name,
        "canonical_name": canonical_name,
        "deep_annotation_present": bool(stage_data.get("annotation_exists")),
        "evidence": _critical_stage_evidence(stage_data),
    }


def build_critical_coverage(parsed: Dict[str, Any], cross_reference: Dict[str, Any]) -> Dict[str, Any]:
    functions = {str(f.get("canonical_name", "")): f for f in _function_index_functions(parsed.get("function_index"))}
    critical_stage_to_function = cross_reference.get("critical_stage_to_function", {})
    records: List[Tuple[str, str, Dict[str, Any], Optional[Dict[str, Any]]]] = []
    for stage_name, stage_data in critical_stage_to_function.items():
        if not isinstance(stage_data, dict):
            continue
        canonical = str(stage_data.get("canonical_name", ""))
        records.append((str(stage_name), canonical, stage_data, functions.get(canonical)))

    generic_mm2_exists = any(
        "nonquant" in str(function.get("canonical_name", "")).lower()
        and "computemm2" in str(function.get("canonical_name", "")).lower()
        for function in functions.values()
    )

    required_items: Dict[str, Any] = {}
    missing_items: List[str] = []
    for item, tokens in REQUIRED_CRITICAL_ITEMS.items():
        matches: List[Dict[str, str]] = []
        exact_matches: List[Dict[str, Any]] = []
        alias_matches: List[Dict[str, Any]] = []
        identity_matches: List[Dict[str, Any]] = []
        for stage_name, canonical, stage_data, function_data in records:
            match = _critical_match(stage_name, canonical, stage_data)
            if stage_name == item:
                exact_matches.append(match)
            elif stage_name in CRITICAL_STAGE_ALIASES.get(item, []):
                alias_matches.append(match)
            elif not _is_known_critical_stage(stage_name) and _identity_matches_required_item(item, tokens, stage_name, canonical, stage_data, function_data):
                identity_matches.append(match)
        if exact_matches:
            matches = exact_matches
        elif alias_matches:
            matches = alias_matches
        else:
            matches = identity_matches
        optional_absent = item == "generic.mm2" and not generic_mm2_exists
        present = bool(matches) or optional_absent
        first_match = matches[0] if matches else {}
        required_items[item] = {
            "present": present,
            "matched_stage": first_match.get("stage"),
            "matched_function": first_match.get("canonical_name"),
            "deep_annotation_present": bool(first_match.get("deep_annotation_present")),
            "evidence": first_match.get("evidence", []),
            "optional_absent": optional_absent,
            "matches": matches,
            "tokens": tokens,
        }
        if not present:
            missing_items.append(item)

    function_to_annotation = cross_reference.get("function_to_annotation", {})
    missing_deep: List[Dict[str, str]] = []
    covered = 0
    total = 0
    for stage_name, canonical, stage_data, function_data in records:
        requires_deep = bool(stage_data.get("annotation_path")) or (
            isinstance(function_data, dict) and str(function_data.get("extraction_level", "")).lower() == "deep"
        )
        if not requires_deep:
            continue
        total += 1
        annotation = function_to_annotation.get(canonical, {}) if isinstance(function_to_annotation, dict) else {}
        annotation_path = str(annotation.get("annotation_path") or stage_data.get("annotation_path") or "")
        if annotation.get("level") == "deep" and annotation.get("annotation_exists"):
            covered += 1
        else:
            missing_deep.append({"stage": stage_name, "canonical_name": canonical, "annotation_path": annotation_path})

    return {
        "required_items": required_items,
        "missing_items": missing_items,
        "critical_path_deep_coverage": {
            "total": total,
            "covered": covered,
            "missing": missing_deep,
            "passed": total > 0 and covered == total,
        },
    }


def build_source_spot_check_plan(parsed: Dict[str, Any], cross_reference: Dict[str, Any]) -> Dict[str, Any]:
    functions = {str(f.get("canonical_name", "")): f for f in _function_index_functions(parsed.get("function_index"))}
    critical_checks: List[Dict[str, Any]] = []
    for stage_name, stage_data in cross_reference.get("critical_stage_to_function", {}).items():
        if not isinstance(stage_data, dict):
            continue
        canonical = str(stage_data.get("canonical_name", ""))
        function = functions.get(canonical, {})
        critical_checks.append(
            {
                "stage": stage_name,
                "canonical_name": canonical,
                "file": function.get("file"),
                "line_range": function.get("line_range"),
                "annotation_path": stage_data.get("annotation_path"),
                "checks": [
                    "Verify function identity and template specialization.",
                    "Verify pipeline stage behavior against source lines.",
                    "Verify cited evidence supports DSL fields and constraints.",
                ],
            }
        )

    card_checks: List[Dict[str, Any]] = []
    for card_data in cross_reference.get("cards_to_evidence", []):
        if not isinstance(card_data, dict):
            continue
        card_checks.append(
            {
                "id": card_data.get("id"),
                "evidence": card_data.get("evidence", []),
                "checks": [
                    "Verify optimization preconditions.",
                    "Verify risk and constraint coverage.",
                ],
            }
        )

    return {
        "critical_functions": critical_checks,
        "optimization_cards": card_checks,
        "recommended_sample": {
            "critical_functions": min(10, len(critical_checks)),
            "optimization_cards": min(10, len(card_checks)),
        },
    }


def _parse_important_files(input_dir: Path) -> Dict[str, Any]:
    parsed: Dict[str, Any] = {}
    for name, relative in IMPORTANT_FILES.items():
        parsed[name] = _load_if_exists(input_dir, relative)
    return parsed


def build_evidence_pack(input_dir: Path, source_root: Optional[Path]) -> Dict[str, Any]:
    parsed = _parse_important_files(input_dir)
    inventory = collect_inventory(input_dir)
    cross_reference = build_cross_reference(input_dir, parsed, inventory)
    critical_coverage = build_critical_coverage(parsed, cross_reference)

    critical_functions: Dict[str, Any] = {}
    missing_critical_functions: List[str] = []
    for stage_name, stage_data in cross_reference.get("critical_stage_to_function", {}).items():
        if not isinstance(stage_data, dict):
            continue
        canonical = str(stage_data.get("canonical_name", ""))
        annotation = cross_reference.get("function_to_annotation", {}).get(canonical, {})
        complete = bool(annotation.get("template_identity_complete"))
        critical_functions[canonical] = {
            "complete": complete,
            "stage": stage_name,
            "missing_fields": annotation.get("template_identity_missing_fields", []),
        }
        if not complete:
            missing_critical_functions.append(canonical)

    source_spot_check_plan = build_source_spot_check_plan(parsed, cross_reference)

    blocking_findings: List[str] = []
    if not inventory["important_files"]["function_index"]["exists"]:
        blocking_findings.append("missing_function_index")
    if not inventory["important_files"]["critical_path"]["exists"]:
        blocking_findings.append("missing_critical_path_annotations")
    if critical_coverage["missing_items"]:
        blocking_findings.append("critical_required_coverage_failed")
    if inventory["important_files"]["critical_path"]["exists"] and not critical_coverage["critical_path_deep_coverage"]["passed"]:
        blocking_findings.append("critical_path_deep_coverage_failed")
    if missing_critical_functions:
        blocking_findings.append("template_identity_coverage_failed")

    return {
        "input_dir": str(input_dir),
        "source_root": str(source_root) if source_root is not None else None,
        "inventory": inventory,
        "cross_reference": cross_reference,
        "critical_coverage": critical_coverage,
        "template_identity_coverage": {
            "critical_functions": critical_functions,
            "missing_critical_functions": missing_critical_functions,
        },
        "source_spot_check_plan": source_spot_check_plan,
        "blocking_findings": blocking_findings,
    }


def write_review_context(output_dir: Path, evidence_pack: Dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_json_yaml(output_dir / "evidence_pack.yaml", evidence_pack)
    dump_json_yaml(output_dir / "inventory.yaml", evidence_pack["inventory"])
    dump_json_yaml(output_dir / "cross_reference.yaml", evidence_pack["cross_reference"])
    dump_json_yaml(output_dir / "source_spot_check_plan.yaml", evidence_pack["source_spot_check_plan"])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare Stage-1 AI review evidence context.")
    parser.add_argument("--input", required=True, help="Stage-1 extraction output directory")
    parser.add_argument("--output", required=True, help="Directory for generated review context")
    parser.add_argument("--source-root", help="Optional source tree root for reviewer orientation")
    args = parser.parse_args(argv)

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    source_root = Path(args.source_root) if args.source_root else None

    if not input_dir.exists() or not input_dir.is_dir():
        print(json.dumps({"error": "input directory missing", "input_dir": str(input_dir)}, ensure_ascii=False), file=sys.stderr)
        return 2

    evidence_pack = build_evidence_pack(input_dir, source_root)
    write_review_context(output_dir, evidence_pack)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "blocking_findings": evidence_pack["blocking_findings"],
                "counts": evidence_pack["inventory"]["counts"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
