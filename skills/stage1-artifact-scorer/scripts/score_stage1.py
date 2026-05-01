#!/usr/bin/env python3
"""Legacy structural pre-scorer for Stage-1 AscendC Attention DSL extraction artifacts.

This script is a heuristic smoke test. It does not assign final Stage-2 readiness
and does not prove source-level accuracy. Prefer prepare_review_context.py followed
by AI review for real Stage-1 artifact review.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

REQUIRED_STRUCTURES = [
    ("interface_tiling", ["interface", "tilingData", "tiling", "workspace"]),
    ("shape_layout", ["shape", "layout", "B", "S1", "S2", "N", "G", "D", "varlen"]),
    ("core_mapping", ["core", "blockIdx", "multiCore", "split", "axis_mapping"]),
    ("s1_s2_or_kv_loop", ["S1", "S2", "kv_block", "kvBlock", "KV", "loop"]),
    ("pipeline", ["BMM1", "Vec1", "BMM2", "Vec2", "pipeline", "qk", "pv"]),
    ("memory_hierarchy", ["GM", "UB", "L1", "L0", "LocalTensor", "DataCopy"]),
    ("l1_residency_partition", ["L1", "residency", "resident", "partition", "常驻", "切分"]),
    ("sparse_window_mask", ["sparse", "causal", "mask", "band", "prefix", "window"]),
    ("online_softmax_lse", ["online_softmax", "softmax", "LSE", "lse", "max", "sum"]),
    ("workspace_layout", ["workspace", "offset", "alias", "no_alias", "partial"]),
    ("tail_alignment", ["tail", "align", "alignment", "duplicate", "mask"]),
    ("event_sync", ["event", "Wait", "SetFlag", "WaitFlag", "MTE", "sync"]),
    ("scalar_offset", ["scalar", "offset", "div", "mod", "hoist", "constexpr"]),
    ("split_kv_merge", ["split_kv", "split-KV", "partial_o", "partial_max", "partial_sum", "merge"]),
    ("knobs_constraints", ["tunable", "knob", "search", "constraint", "risk", "precondition"]),
]

REQUIRED_CARD_FIELDS = [
    "id", "pattern", "intent", "preconditions", "tunable_knobs", "constraints",
    "risks", "possible_dsl_fields", "lowering_hint", "source_evidence"
]

REQUIRED_FUNCTION_FIELDS = [
    "file", "function", "role", "inputs", "outputs", "dataflow", "memory_behavior",
    "pipeline_stage", "tunable_knobs", "constraints", "risks", "possible_dsl_section", "source_evidence"
]


@dataclass
class Score:
    coverage: int
    accuracy: int
    traceability: int
    dsl_convertibility: int
    risks_constraints: int
    dedup: int

    @property
    def total(self) -> int:
        return self.coverage + self.accuracy + self.traceability + self.dsl_convertibility + self.risks_constraints + self.dedup


def read_text_files(root: Path) -> Dict[str, str]:
    texts: Dict[str, str] = {}
    if not root.exists():
        return texts
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".yaml", ".yml", ".json", ".md", ".txt"}:
            try:
                texts[str(p.relative_to(root))] = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
    return texts


def keyword_hit(text: str, keywords: Iterable[str]) -> bool:
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            return True
    return False


def score_coverage(all_text: str) -> Tuple[int, List[Tuple[str, bool]]]:
    hits = []
    for name, kws in REQUIRED_STRUCTURES:
        hits.append((name, keyword_hit(all_text, kws)))
    hit_count = sum(1 for _, ok in hits if ok)
    return round(25 * hit_count / len(REQUIRED_STRUCTURES)), hits


def section_texts(files: Dict[str, str], names: List[str]) -> str:
    parts = []
    for path, text in files.items():
        if any(n in path.lower() for n in names):
            parts.append(text)
    return "\n".join(parts)


def count_field_mentions(text: str, fields: List[str]) -> Tuple[int, List[str]]:
    missing = []
    for f in fields:
        if re.search(rf"\b{re.escape(f)}\b\s*:", text) is None and f not in text:
            missing.append(f)
    return len(fields) - len(missing), missing


def estimate_traceability(all_text: str) -> int:
    evidence_terms = ["source_evidence", "file:", "function:", "line", "behavior:", "repo:", "commit:"]
    hits = sum(1 for t in evidence_terms if t.lower() in all_text.lower())
    return min(15, round(15 * hits / len(evidence_terms)))


def estimate_dsl_convertibility(all_text: str) -> int:
    terms = [
        "possible_dsl", "possible_dsl_fields", "dsl_fields", "module", "field", "enum",
        "searchable", "validator", "lowering", "lowering_hint", "constraint", "transform"
    ]
    hits = sum(1 for t in terms if t.lower() in all_text.lower())
    return min(20, round(20 * hits / len(terms)))


def estimate_risks_constraints(all_text: str) -> int:
    terms = ["risk", "risks", "constraint", "precondition", "no_alias", "overflow", "deadlock", "alignment", "forbidden", "guard"]
    hits = sum(1 for t in terms if t.lower() in all_text.lower())
    return min(10, round(10 * hits / len(terms)))


def estimate_dedup(cards_text: str) -> int:
    if not cards_text.strip():
        return 0
    has_alias = "aliases" in cards_text or "canonical" in cards_text
    ids = re.findall(r"\bid\s*:\s*([A-Za-z0-9_\-\.]+)", cards_text)
    if not ids:
        return 2 if has_alias else 1
    duplicate_count = len(ids) - len(set(ids))
    score = 5
    if duplicate_count > 0:
        score -= min(3, duplicate_count)
    if not has_alias:
        score -= 1
    return max(0, score)


def readiness(score: Score) -> str:
    if score.coverage < 18 or score.accuracy < 20 or score.dsl_convertibility < 15:
        if score.total >= 70:
            return "READY_WITH_FIXES_BLOCKED_BY_GATE"
        return "NEEDS_REEXTRACTION"
    if score.total >= 85:
        return "READY_FOR_STAGE2"
    if score.total >= 70:
        return "READY_WITH_FIXES"
    if score.total >= 50:
        return "NEEDS_REEXTRACTION"
    return "NOT_USABLE"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Stage-1 output directory")
    ap.add_argument("--output", required=True, help="Review output directory")
    args = ap.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = read_text_files(input_dir)
    all_text = "\n".join(files.values())
    cards_text = section_texts(files, ["card", "cards"])
    annotations_text = section_texts(files, ["annotation", "annotations"])

    coverage, coverage_hits = score_coverage(all_text)
    card_fields_present, card_missing = count_field_mentions(cards_text, REQUIRED_CARD_FIELDS)
    func_fields_present, func_missing = count_field_mentions(annotations_text, REQUIRED_FUNCTION_FIELDS)

    traceability = estimate_traceability(all_text)
    dsl_convertibility = estimate_dsl_convertibility(all_text)
    risks_constraints = estimate_risks_constraints(all_text)
    dedup = estimate_dedup(cards_text)

    # Accuracy cannot be reliably proven without source-aware review. Give a conservative structural estimate.
    source_like_terms = ["file:", "function:", "behavior:", "source_evidence"]
    structure_terms = ["loop_order", "memory", "pipeline", "dataflow", "constraints", "preconditions"]
    source_hits = sum(1 for t in source_like_terms if t.lower() in all_text.lower())
    structure_hits = sum(1 for t in structure_terms if t.lower() in all_text.lower())
    accuracy = min(25, round(10 + 15 * (source_hits + structure_hits) / (len(source_like_terms) + len(structure_terms)))) if all_text else 0

    score = Score(
        coverage=coverage,
        accuracy=accuracy,
        traceability=traceability,
        dsl_convertibility=dsl_convertibility,
        risks_constraints=risks_constraints,
        dedup=dedup,
    )

    result = {
        "score": {
            "coverage": score.coverage,
            "accuracy_structural_estimate": score.accuracy,
            "traceability": score.traceability,
            "dsl_convertibility": score.dsl_convertibility,
            "risks_constraints": score.risks_constraints,
            "dedup_canonicalization": score.dedup,
            "total": score.total,
        },
        "structural_readiness_hint": readiness(score),
        "coverage_matrix": {name: ok for name, ok in coverage_hits},
        "missing_required_card_fields": card_missing,
        "missing_required_function_annotation_fields": func_missing,
        "notes": [
            "This is a legacy structural pre-score, not an AI review.",
            "Do not use accuracy_structural_estimate as final source accuracy.",
            "Prefer prepare_review_context.py plus source-aware AI review for Stage-2 readiness.",
            "Accuracy is a structural estimate only. Final review must inspect source code evidence.",
            "Use this output as a pre-score before LLM/source-aware review.",
            "structural_readiness_hint is not final Stage-2 readiness."
        ],
        "file_count": len(files),
    }

    (output_dir / "scorecard.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = []
    lines.append("# Stage-1 Artifact Structural Pre-Score\n")
    lines.append(f"Overall: **{score.total}/100**")
    lines.append(f"Structural readiness hint: **{result['structural_readiness_hint']}**\n")
    lines.append("## Breakdown\n")
    for k, v in result["score"].items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## Coverage Matrix\n")
    for name, ok in coverage_hits:
        lines.append(f"- [{'x' if ok else ' '}] {name}")
    lines.append("\n## Missing required card fields\n")
    if card_missing:
        lines.extend(f"- {x}" for x in card_missing)
    else:
        lines.append("- None detected")
    lines.append("\n## Missing required function annotation fields\n")
    if func_missing:
        lines.extend(f"- {x}" for x in func_missing)
    else:
        lines.append("- None detected")
    lines.append("\n## Important note\n")
    lines.append("This is a structural pre-score. The final score must be assigned after source-aware review of key claims.")
    (output_dir / "score_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
