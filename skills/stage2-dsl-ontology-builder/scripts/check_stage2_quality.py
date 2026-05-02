#!/usr/bin/env python3
"""Check Stage 2 ATDSL output quality using structural gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

REQUIRED = [
    "ontology/modules.yaml",
    "ontology/canonical_optimizations.yaml",
    "ontology/field_policy.yaml",
    "schema/atdsl.schema.yaml",
    "examples/fa_forward_shadow.yaml",
    "examples/flash_decode_shadow.yaml",
    "review/schema_review.md",
    "review/coverage_matrix.md",
    "review/missing_fields.md",
]

VALIDATORS = [
    "ub_capacity.yaml",
    "l1_capacity.yaml",
    "workspace_no_alias.yaml",
    "sparse_window_alignment.yaml",
    "split_kv_lse_merge_valid.yaml",
    "event_dependency_valid.yaml",
    "l1_residency_loop_order.yaml",
]

LOWERING = [
    "LowerTiling.yaml",
    "LowerCoreMapping.yaml",
    "LowerSparseWindow.yaml",
    "LowerL1Partition.yaml",
    "LowerL1Residency.yaml",
    "LowerDecodeLoopNest.yaml",
    "LowerWorkspaceLayout.yaml",
    "LowerPipeline.yaml",
]

KEY_TERMS = {
    "l1_residency": ["l1_residency", "residency", "across_g"],
    "l1_partition": ["l1_partition", "policy", "kv_split"],
    "split_kv": ["split_kv", "partial_o", "partial_max", "partial_sum", "online_lse_merge"],
    "workspace": ["workspace", "no_alias", "unique_offset"],
    "pipeline": ["pipeline", "ring_depth", "events"],
    "sparse_window": ["sparse_window", "s2", "align"],
}


def read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").lower()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="stage2_outputs")
    args = parser.parse_args()
    root = Path(args.input)

    issues: List[str] = []
    scores = {
        "card_to_module_coverage": 20,
        "field_design_completeness": 20,
        "searchable_knob_quality": 15,
        "validator_completeness": 20,
        "lowering_spec_clarity": 10,
        "shadow_dsl_coverage": 15,
    }

    for rel in REQUIRED:
        if not (root / rel).exists():
            issues.append(f"Missing required file: {rel}")
            if rel.startswith("ontology"):
                scores["card_to_module_coverage"] -= 5
            elif rel.startswith("schema"):
                scores["field_design_completeness"] -= 5
            elif rel.startswith("examples"):
                scores["shadow_dsl_coverage"] -= 5

    for fname in VALIDATORS:
        if not (root / "validators_spec" / fname).exists():
            issues.append(f"Missing validator: {fname}")
            scores["validator_completeness"] -= 3

    for fname in LOWERING:
        if not (root / "lowering_spec" / fname).exists():
            issues.append(f"Missing lowering spec: {fname}")
            scores["lowering_spec_clarity"] -= 2

    all_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore").lower() for p in root.rglob("*") if p.is_file()) if root.exists() else ""
    for name, terms in KEY_TERMS.items():
        missing = [t for t in terms if t not in all_text]
        if missing:
            issues.append(f"Weak coverage for {name}: missing terms {missing}")
            scores["field_design_completeness"] -= 2

    # Penalize placeholder evidence if too much.
    placeholders = all_text.count("needs evidence") + all_text.count("needs_evidence") + all_text.count("needs review")
    if placeholders > 20:
        issues.append(f"Too many placeholder evidence markers: {placeholders}")
        scores["card_to_module_coverage"] -= 4
        scores["field_design_completeness"] -= 4

    # Clamp scores.
    for k in list(scores):
        scores[k] = max(0, scores[k])
    total = sum(scores.values())
    status = "pass" if total >= 85 and not any("Missing" in i for i in issues) else "warn" if total >= 70 else "fail"
    result = {
        "overall_status": status,
        "total_score": total,
        "scores": scores,
        "issues": issues,
        "next_actions": [
            "Map placeholder evidence fields to source_evidence entries.",
            "Ensure high-risk fields have validators.",
            "Generate or refine shadow DSL from mature kernels.",
        ],
    }

    out = root / "review" / "quality_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# Stage 2 Quality Gate", "", f"Status: **{status}**", f"Total score: **{total}/100**", "", "## Scores", ""]
    for k, v in scores.items():
        md.append(f"- {k}: {v}")
    md += ["", "## Issues", ""]
    md += [f"- {i}" for i in issues] or ["- No structural issues found."]
    (root / "review" / "quality_gate.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
