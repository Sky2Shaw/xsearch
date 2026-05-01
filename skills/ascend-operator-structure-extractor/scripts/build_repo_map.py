#!/usr/bin/env python3
"""Build a repository map and approximate function index for AscendC operators."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


SOURCE_EXTENSIONS = {".h", ".hpp", ".hh", ".c", ".cc", ".cpp", ".cxx", ".ascendc"}
TEST_DIR_NAMES = {"test", "tests", "unittest", "unittests", "ut", "gtest"}
TEST_FILE_PATTERNS = [
    re.compile(r".*_test\.[^.]+$"),
    re.compile(r"test_.*\.[^.]+$"),
    re.compile(r".*_unittest\.[^.]+$"),
]
CONTROL_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "else",
    "do",
    "return",
    "sizeof",
    "static_assert",
    "constexpr",
    "likely",
    "unlikely",
}
CALL_EXCLUDES = CONTROL_KEYWORDS | {
    "alignas",
    "alignof",
    "decltype",
    "new",
    "delete",
    "operator",
}

DEEP_NAME_PATTERNS = [
    "Process",
    "ProcessMm1",
    "ProcessMm2",
    "InitBuffer",
    "Init",
    "ComputeMm1",
    "ComputeMm2",
    "ComputeBmm1",
    "ComputeBmm2",
    "ComputeConstexpr",
    "ComputeAxisIdx",
    "GetS2LoopRange",
    "SetExtraInfo",
    "IterateBmm1",
    "IterateBmm2",
    "ProcessVec1",
    "ProcessVec2",
    "ComputeBmm1Tail",
    "Bmm1",
    "Bmm2",
    "Mmad",
    "Matmul",
    "DataCopy",
    "WorkspaceOffset",
    "BlockTable",
    "KvCache",
    "KVCache",
    "SplitKv",
    "SplitKV",
    "LseMerge",
    "LSEMerge",
    "Softmax",
]
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
MEMORY_TENSOR_SIGNALS = [
    "GlobalTensor",
    "LocalTensor",
    "TPipe",
    "TBuf",
    "TQue",
    "L1",
    "L0A",
    "L0B",
    "L0C",
    "UB",
    "GM",
]
COMPUTE_SYNC_SIGNALS = [
    "DataCopy",
    "Bmm",
    "BMM",
    "Matmul",
    "Softmax",
    "LSE",
    "WaitFlag",
    "SetFlag",
    "MTE2",
    "MTE3",
    "vector",
    "cube",
]
STRUCTURE_SIGNALS = [
    "tiling",
    "workspace",
    "sparse",
    "actualSeq",
    "blockTable",
    "split",
    "taskId",
    "extraInfo",
    "s1",
    "s2",
    "kvBlock",
    "tail",
    "align",
    "mask",
]
TAIL_ALIGNMENT_MASK_SIGNALS = ["tail", "align", "mask"]
PERFORMANCE_SIGNALS = (
    DEEP_NAME_PATTERNS + MEMORY_TENSOR_SIGNALS + COMPUTE_SYNC_SIGNALS + STRUCTURE_SIGNALS
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build AscendC operator repository map and function index"
    )
    parser.add_argument("--target-dir", required=True, help="Operator source directory to scan")
    parser.add_argument("--output-root", required=True, help="Extraction output root")
    parser.add_argument("--max-files", type=int, help="Maximum source files to scan")
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include files under test/tests paths",
    )
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
    lines: list[str] = []
    if isinstance(value, dict):
        if not value:
            return [space + "{}"]
        for key, item in value.items():
            rendered_key = yaml_scalar(key)
            if isinstance(item, (dict, list)):
                lines.append(f"{space}{rendered_key}:")
                lines.extend(to_yaml(item, indent + 2))
            else:
                lines.append(f"{space}{rendered_key}: {yaml_scalar(item)}")
    elif isinstance(value, list):
        if not value:
            return [space + "[]"]
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{space}-")
                lines.extend(to_yaml(item, indent + 2))
            else:
                lines.append(f"{space}- {yaml_scalar(item)}")
    else:
        lines.append(space + yaml_scalar(value))
    return lines


def write_yaml(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(to_yaml(value)) + "\n", encoding="utf-8")


def is_test_path(path: Path) -> bool:
    if any(part.lower() in TEST_DIR_NAMES for part in path.parts[:-1]):
        return True
    return any(pattern.fullmatch(path.name.lower()) for pattern in TEST_FILE_PATTERNS)


def collect_source_files(target_dir: Path, include_tests: bool, max_files: int | None) -> tuple[list[Path], list[dict[str, Any]]]:
    found: list[Path] = []
    skipped: list[dict[str, Any]] = []
    for path in sorted(target_dir.rglob("*")):
        if not path.is_file() or path.suffix not in SOURCE_EXTENSIONS:
            continue
        relative = path.relative_to(target_dir)
        if not include_tests and is_test_path(relative):
            skipped.append({"path": str(relative), "reason": "test_path"})
            continue
        if max_files is not None and len(found) >= max_files:
            skipped.append({"path": str(relative), "reason": "max_files_limit"})
            continue
        found.append(path)
    return found, skipped


def sanitize_cpp_like_text(text: str) -> str:
    """Return same-length text with comments and literals blanked.

    This is a best-effort C/C++/AscendC scanner helper, not a lexer. It handles
    ordinary strings, char literals, line comments, block comments, and common
    raw strings conservatively while preserving newlines and character indices.
    """
    result = list(text)
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        next_char = text[index + 1] if index + 1 < length else ""

        if char == "/" and next_char == "/":
            result[index] = " "
            result[index + 1] = " "
            index += 2
            while index < length and text[index] != "\n":
                result[index] = " "
                index += 1
            continue

        if char == "/" and next_char == "*":
            result[index] = " "
            result[index + 1] = " "
            index += 2
            while index < length - 1:
                if text[index] == "\n":
                    index += 1
                    continue
                if text[index] == "*" and text[index + 1] == "/":
                    result[index] = " "
                    result[index + 1] = " "
                    index += 2
                    break
                result[index] = " "
                index += 1
            continue

        if char == "R" and next_char == '"':
            delimiter_start = index + 2
            paren = text.find("(", delimiter_start, min(length, delimiter_start + 32))
            if paren != -1:
                delimiter = text[delimiter_start:paren]
                terminator = ")" + delimiter + '"'
                end = text.find(terminator, paren + 1)
                if end != -1:
                    stop = end + len(terminator)
                    while index < stop:
                        if text[index] != "\n":
                            result[index] = " "
                        index += 1
                    continue

        if char in {"'", '"'}:
            quote = char
            result[index] = " "
            index += 1
            escaped = False
            while index < length:
                current = text[index]
                if current != "\n":
                    result[index] = " "
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    index += 1
                    break
                index += 1
            continue

        index += 1
    return "".join(result)


def brace_delta(line: str) -> int:
    return line.count("{") - line.count("}")


def extract_class_context(lines: list[str], line_index: int) -> str | None:
    stack: list[tuple[str, int]] = []
    class_re = re.compile(r"\b(?:class|struct)\s+([A-Za-z_]\w*)[^;{]*\{")
    for index, line in enumerate(lines[:line_index]):
        match = class_re.search(line)
        if match:
            stack.append((match.group(1), 1))
            tail = line[match.end() :]
            stack[-1] = (stack[-1][0], stack[-1][1] + tail.count("{") - tail.count("}"))
            continue
        if stack:
            name, depth = stack[-1]
            depth += brace_delta(line)
            if depth <= 0:
                stack.pop()
            else:
                stack[-1] = (name, depth)
    return stack[-1][0] if stack else None


def signature_candidate(lines: list[str], start: int) -> tuple[str, int] | None:
    parts: list[str] = []
    for index in range(start, min(start + 8, len(lines))):
        clean = lines[index].strip()
        if not clean:
            continue
        parts.append(clean)
        joined = " ".join(parts)
        if ";" in joined and "{" not in joined:
            return None
        if "{" in joined:
            before_open = joined[: joined.index("{")]
            if ";" in before_open:
                return None
            return joined[: joined.index("{") + 1], index
    return None


def normalize_cpp_name(name: str) -> str:
    text = re.sub(r"\s+", " ", name).strip()
    text = re.sub(r"\s*::\s*", "::", text)
    text = re.sub(r"\s*<\s*", "<", text)
    text = re.sub(r"\s*>\s*", ">", text)
    text = re.sub(r"\s*,\s*", ",", text)
    return text


def split_template_args(text: str) -> list[str]:
    start = text.find("<")
    end = text.rfind(">")
    if start == -1 or end == -1 or end <= start:
        return []
    body = text[start + 1 : end]
    args: list[str] = []
    depth = 0
    current: list[str] = []
    for char in body:
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        if char == "," and depth == 0:
            args.append(normalize_cpp_name("".join(current)))
            current = []
        else:
            current.append(char)
    if current:
        args.append(normalize_cpp_name("".join(current)))
    return [arg for arg in args if arg]


def strip_template_args(text: str) -> str:
    result: list[str] = []
    depth = 0
    for char in text:
        if char == "<":
            depth += 1
            continue
        if char == ">" and depth:
            depth -= 1
            continue
        if depth == 0:
            result.append(char)
    return normalize_cpp_name("".join(result))


def split_owner_and_name(qualified_name: str) -> tuple[str | None, str]:
    normalized = normalize_cpp_name(qualified_name)
    if "::" not in normalized:
        return None, normalized.split("::")[-1].lstrip("~")
    owner, name = normalized.rsplit("::", 1)
    return owner, name.lstrip("~")


def owner_base_name(owner: str | None) -> str | None:
    if owner is None:
        return None
    return strip_template_args(owner).split("::")[-1]


def extract_template_declarations(text: str) -> list[str]:
    declarations: list[str] = []
    cursor = 0
    while True:
        match = re.search(r"\btemplate\s*<", text[cursor:])
        if not match:
            break
        start = cursor + match.start()
        open_index = text.find("<", start)
        depth = 0
        end_index: int | None = None
        for index in range(open_index, len(text)):
            if text[index] == "<":
                depth += 1
            elif text[index] == ">":
                depth -= 1
                if depth == 0:
                    end_index = index
                    break
        if end_index is None:
            break
        declarations.append(normalize_cpp_name(text[start : end_index + 1]))
        cursor = end_index + 1
    return declarations


def extract_template_context(lines: list[str], line_index: int, signature: str = "") -> list[str]:
    inline_templates = extract_template_declarations(signature)
    if inline_templates:
        return inline_templates

    templates: list[str] = []
    cursor = line_index - 1
    while cursor >= 0:
        stripped = lines[cursor].strip()
        if not stripped:
            cursor -= 1
            continue
        if stripped.startswith("template"):
            templates.insert(0, normalize_cpp_name(stripped))
            cursor -= 1
            continue
        break
    return templates


def infer_variant(file_path: str, canonical_name: str, owner: str | None) -> str:
    haystack = f"{file_path} {canonical_name} {owner or ''}".lower()
    if "flashdecode" in haystack or "flash_decode" in haystack:
        return "flash_decode"
    if "mla" in haystack:
        return "mla"
    if "gqa" in haystack:
        return "gqa"
    if "nonquant" in haystack:
        return "nonquant"
    return "unknown"


def infer_stage(name: str, canonical_name: str, body: str) -> str:
    haystack = f"{name} {canonical_name} {body[:500]}".lower()
    if "mm2" in haystack or "bmm2" in haystack:
        return "mm2"
    if "mm1" in haystack or "bmm1" in haystack:
        return "mm1"
    if "vec1" in haystack:
        return "vec1"
    if "vec2" in haystack:
        return "vec2"
    if "softmax" in haystack:
        return "softmax"
    if "flashdecode" in haystack or "flash_decode" in haystack or "lsemerge" in haystack:
        return "flash_decode"
    if "workspace" in haystack:
        return "workspace"
    if "tiling" in haystack:
        return "tiling"
    if "metadata" in haystack:
        return "metadata"
    return "unknown"


def extract_qualified_from_prefix(prefix: str) -> str | None:
    cursor = len(prefix) - 1
    while cursor >= 0 and prefix[cursor].isspace():
        cursor -= 1
    if cursor < 0:
        return None

    chars: list[str] = []
    depth = 0
    while cursor >= 0:
        char = prefix[cursor]
        if char == ">":
            depth += 1
            chars.append(char)
            cursor -= 1
            continue
        if char == "<" and depth:
            depth -= 1
            chars.append(char)
            cursor -= 1
            continue
        if depth == 0 and char.isspace():
            break
        if depth == 0 and not re.match(r"[A-Za-z0-9_:~]", char):
            break
        chars.append(char)
        cursor -= 1

    qualified = "".join(reversed(chars)).strip()
    if not qualified or not re.search(r"[A-Za-z_]", qualified):
        return None
    return normalize_cpp_name(qualified)


def parse_function_signature(signature: str) -> tuple[str, str] | None:
    if "(" not in signature or ")" not in signature:
        return None
    prefix = signature[: signature.index("(")].strip()
    if not prefix:
        return None
    first = prefix.split()[0].lstrip("~")
    if first in CONTROL_KEYWORDS:
        return None
    prefix_for_name = re.sub(r"\s*::\s*", "::", prefix)
    qualified = extract_qualified_from_prefix(prefix_for_name)
    if qualified is None:
        return None
    owner, name = split_owner_and_name(qualified)
    if name in CONTROL_KEYWORDS:
        return None
    return name, qualified


def find_function_end(lines: list[str], open_line: int) -> int:
    balance = 0
    seen_open = False
    for index in range(open_line, len(lines)):
        clean = lines[index]
        for char in clean:
            if char == "{":
                balance += 1
                seen_open = True
            elif char == "}":
                balance -= 1
                if seen_open and balance <= 0:
                    return index
    return len(lines) - 1


def extract_calls(body: str, own_name: str) -> list[str]:
    calls: list[str] = []
    seen: set[str] = set()
    for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body):
        if name == own_name or name in CALL_EXCLUDES:
            continue
        if name not in seen:
            seen.add(name)
            calls.append(name)
    return calls


def is_simple_accessor(name: str, body: str) -> bool:
    compact = re.sub(r"\s+", " ", body.strip())
    if re.match(r"^(Get|Set|Is|Has)[A-Z_]", name) and len(compact) < 180:
        call_count = len(re.findall(r"\b[A-Za-z_]\w*\s*\(", body))
        if call_count <= 1 and not any(signal in body for signal in COMPUTE_SYNC_SIGNALS):
            return True
    return bool(re.fullmatch(r"\{\s*(return\s+[^;]+;|[^;{}]+=[^;{}]+;)?\s*\}", compact))


def classify_role(name: str, body: str) -> str:
    haystack = f"{name}\n{body}"
    lower = haystack.lower()
    if name in {"Process", "Main", "Kernel"} or name.lower() == "main":
        return "main_process"
    if any(signal in haystack for signal in ["WorkspaceOffset", "workspace"]) or "address" in lower:
        return "workspace_or_address_helper"
    if any(signal in haystack for signal in ["KvCache", "KVCache", "kvCache", "kvBlock", "BlockTable", "blockTable"]):
        return "decode_kv_cache"
    if any(signal in haystack for signal in ["sparse", "mask", "actualSeq", "GetS2LoopRange", "s1", "s2"]):
        return "sparse_or_mask_range"
    if "DataCopy" in haystack:
        return "memory_transfer"
    if any(signal in haystack for signal in ["Bmm", "BMM", "Matmul", "cube"]):
        return "cube_compute"
    if any(signal in haystack for signal in ["Softmax", "LSE", "LseMerge", "LSEMerge"]):
        return "vector_softmax_or_lse"
    if is_simple_accessor(name, body):
        return "simple_accessor_or_wrapper"
    return "unknown"


def score_function(name: str, body: str, role: str, stage: str) -> tuple[int, list[str]]:
    score = 10
    reasons: list[str] = []
    haystack = f"{name}\n{body}"
    known_deep_name = any(pattern in name for pattern in DEEP_NAME_PATTERNS)

    if known_deep_name:
        score += 60
        reasons.append("known_deep_name_pattern")
    if name in {"Process", "Main"} or name.lower() == "main":
        score += 25
        reasons.append("process_or_main_path")
    if name in CRITICAL_STAGE_FUNCTIONS:
        score += 40
        reasons.append("critical_attention_stage_function")
    if stage in {"mm1", "mm2", "vec1", "vec2"}:
        score += 25
        reasons.append(f"attention_stage:{stage}")
    memory_hits = [signal for signal in MEMORY_TENSOR_SIGNALS if re.search(rf"\b{re.escape(signal)}\b", haystack)]
    if memory_hits:
        score += min(20, 5 * len(memory_hits))
        reasons.append("memory_tensor_api:" + ",".join(memory_hits[:6]))
    compute_hits = [signal for signal in COMPUTE_SYNC_SIGNALS if re.search(rf"\b{re.escape(signal)}\b", haystack)]
    if compute_hits:
        score += min(30, 5 * len(compute_hits))
        reasons.append("compute_sync_api:" + ",".join(compute_hits[:8]))
    structure_hits = [signal for signal in STRUCTURE_SIGNALS if signal in haystack]
    if structure_hits:
        score += min(20, 4 * len(structure_hits))
        reasons.append("structure_signal:" + ",".join(structure_hits[:8]))
    if re.search(r"\b(if|else|switch|for|while)\b", body):
        score += 8
        reasons.append("branch_signal")
    if any(signal in haystack for signal in TAIL_ALIGNMENT_MASK_SIGNALS):
        score += 8
        reasons.append("tail_alignment_or_mask_signal")
    if role == "simple_accessor_or_wrapper":
        score -= 35
        reasons.append("simple_accessor_or_wrapper_penalty")
    if not any(signal in haystack for signal in PERFORMANCE_SIGNALS):
        score -= 15
        reasons.append("no_performance_or_dsl_signal_penalty")

    return max(0, min(100, score)), reasons or ["no_strong_signal"]


def extraction_level(score: int) -> str:
    if score >= 70:
        return "deep"
    if score >= 40:
        return "brief"
    return "index"


def discover_function_candidates(lines: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_open_lines: set[int] = set()
    for index in range(len(lines)):
        candidate = signature_candidate(lines, index)
        if not candidate:
            continue
        signature, open_line = candidate
        if open_line in seen_open_lines:
            continue
        parsed = parse_function_signature(signature)
        if not parsed:
            continue
        name, qualified = parsed
        seen_open_lines.add(open_line)
        candidates.append(
            {
                "signature_start": index,
                "open_line": open_line,
                "signature": signature,
                "name": name,
                "qualified": qualified,
            }
        )
    return candidates


def scan_file(path: Path, target_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [], {
            "path": str(path.relative_to(target_dir)),
            "reason": "read_error",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    sanitized_text = sanitize_cpp_like_text(text)
    lines = text.splitlines()
    sanitized_lines = sanitized_text.splitlines()
    functions: list[dict[str, Any]] = []
    candidates = discover_function_candidates(sanitized_lines)
    for candidate_index, candidate in enumerate(candidates):
        index = candidate["signature_start"]
        open_line = candidate["open_line"]
        name = candidate["name"]
        qualified = candidate["qualified"]
        end_line = find_function_end(sanitized_lines, open_line)
        if candidate_index + 1 < len(candidates):
            next_start = candidates[candidate_index + 1]["signature_start"]
            if open_line < next_start <= end_line:
                end_line = max(open_line, next_start - 1)
        body = "\n".join(lines[open_line : end_line + 1])
        sanitized_body = "\n".join(sanitized_lines[open_line : end_line + 1])
        class_name = extract_class_context(sanitized_lines, index)
        qualified_name = qualified if "::" in qualified else f"{class_name}::{name}" if class_name else name
        qualified_name = normalize_cpp_name(qualified_name)
        owner, _ = split_owner_and_name(qualified_name)
        canonical_name = qualified_name
        template_params = extract_template_context(lines, index, candidate["signature"])
        relative_file = str(path.relative_to(target_dir))
        stage = infer_stage(name, canonical_name, body)
        variant = infer_variant(relative_file, canonical_name, owner)
        role = classify_role(name, body)
        score, reasons = score_function(name, body, role, stage)
        functions.append(
            {
                "function_id": f"{relative_file}:{index + 1}:{name}",
                "function_name": name,
                "qualified_name": qualified_name,
                "canonical_name": canonical_name,
                "owner": owner_base_name(owner),
                "owner_qualified": owner,
                "owner_template_args": split_template_args(owner or ""),
                "template_params": template_params,
                "variant": variant,
                "stage": stage,
                "file": relative_file,
                "start_line": index + 1,
                "end_line": end_line + 1,
                "rough_role": role,
                "importance_score": score,
                "importance_reasons": reasons,
                "extraction_level": extraction_level(score),
                "calls": extract_calls(sanitized_body, name),
                "called_by": [],
            }
        )
    return functions, None


def populate_called_by(functions: list[dict[str, Any]]) -> None:
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for function in functions:
        by_name[function["function_name"]].append(function)
    for caller in functions:
        for called_name in caller["calls"]:
            for callee in by_name.get(called_name, []):
                callee["called_by"].append(caller["function_name"])
    for function in functions:
        function["called_by"] = sorted(set(function["called_by"]))


def function_annotation(function: dict[str, Any]) -> dict[str, Any]:
    return {
        "function_id": function["function_id"],
        "function_name": function["function_name"],
        "qualified_name": function["qualified_name"],
        "canonical_name": function["canonical_name"],
        "owner": function["owner"],
        "owner_qualified": function["owner_qualified"],
        "owner_template_args": function["owner_template_args"],
        "template_params": function["template_params"],
        "variant": function["variant"],
        "stage": function["stage"],
        "file": function["file"],
        "line_range": {"start": function["start_line"], "end": function["end_line"]},
        "rough_role": function["rough_role"],
        "importance_score": function["importance_score"],
        "importance_reasons": function["importance_reasons"],
        "extraction_level": function["extraction_level"],
        "calls": function["calls"],
        "called_by": function["called_by"],
    }


def safe_annotation_name(function: dict[str, Any], ordinal: int) -> str:
    identity = function.get("canonical_name") or function["function_name"]
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{function['file']}__{identity}")
    if len(stem) > 180:
        digest = hashlib.sha1(stem.encode("utf-8")).hexdigest()[:12]
        stem = f"{stem[:160]}__{digest}"
    return f"{ordinal:04d}_{stem}.yaml"


def main() -> int:
    args = parse_args()
    target_dir = Path(args.target_dir).expanduser().resolve()
    if not target_dir.is_dir():
        print(f"error: --target-dir must exist and be a directory: {target_dir}", file=sys.stderr)
        return 2
    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    files, skipped = collect_source_files(target_dir, args.include_tests, args.max_files)
    functions: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []
    for file_path in files:
        file_functions, skip_reason = scan_file(file_path, target_dir)
        if skip_reason is not None:
            skipped.append(skip_reason)
            continue
        functions.extend(file_functions)
        inventory.append(
            {
                "path": str(file_path.relative_to(target_dir)),
                "extension": file_path.suffix,
                "functions_indexed": len(file_functions),
            }
        )
    populate_called_by(functions)

    reports_dir = output_root / "reports"
    write_yaml(
        reports_dir / "repo_map.yaml",
        {
            "repo_map": {
                "target_dir": str(target_dir),
                "source_extensions": sorted(SOURCE_EXTENSIONS),
                "files_scanned": len(files),
                "functions_indexed": len(functions),
                "include_tests": bool(args.include_tests),
                "max_files": args.max_files,
            }
        },
    )
    write_yaml(reports_dir / "file_inventory.yaml", {"file_inventory": {"files": inventory}})
    write_yaml(
        reports_dir / "function_index.yaml",
        {"function_index": {"functions": [function_annotation(f) for f in functions]}},
    )
    write_yaml(
        reports_dir / "function_importance.yaml",
        {
            "function_importance": {
                "functions": [
                    {
                        "function_name": f["function_name"],
                        "qualified_name": f["qualified_name"],
                        "canonical_name": f["canonical_name"],
                        "owner": f["owner"],
                        "owner_qualified": f["owner_qualified"],
                        "owner_template_args": f["owner_template_args"],
                        "template_params": f["template_params"],
                        "variant": f["variant"],
                        "stage": f["stage"],
                        "file": f["file"],
                        "rough_role": f["rough_role"],
                        "importance_score": f["importance_score"],
                        "importance_reasons": f["importance_reasons"],
                        "extraction_level": f["extraction_level"],
                    }
                    for f in sorted(
                        functions,
                        key=lambda item: (-item["importance_score"], item["file"], item["start_line"]),
                    )
                ]
            }
        },
    )
    write_yaml(
        reports_dir / "skipped_or_shallow_items.yaml",
        {
            "skipped_or_shallow_items": {
                "skipped_files": skipped,
                "shallow_functions": [
                    {
                        "function_name": f["function_name"],
                        "qualified_name": f["qualified_name"],
                        "canonical_name": f["canonical_name"],
                        "owner": f["owner"],
                        "owner_qualified": f["owner_qualified"],
                        "variant": f["variant"],
                        "stage": f["stage"],
                        "file": f["file"],
                        "extraction_level": f["extraction_level"],
                        "importance_score": f["importance_score"],
                    }
                    for f in functions
                    if f["extraction_level"] != "deep"
                ],
            }
        },
    )

    annotation_dir = output_root / "annotations/functions/index"
    annotation_dir.mkdir(parents=True, exist_ok=True)
    for ordinal, function in enumerate(functions, start=1):
        write_yaml(
            annotation_dir / safe_annotation_name(function, ordinal),
            {"function_index_entry": function_annotation(function)},
        )

    print(
        json.dumps(
            {
                "files_scanned": len(files),
                "functions_indexed": len(functions),
                "output_root": str(output_root),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
