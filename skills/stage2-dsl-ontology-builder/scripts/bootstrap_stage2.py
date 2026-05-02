#!/usr/bin/env python3
"""
Bootstrap Stage 2 ATDSL artifacts from Stage 1 outputs.

This script intentionally creates a scaffold, not final truth. It scans Stage 1
artifacts as text, infers common Ascend attention optimization patterns, and
writes Stage 2 output files that Codex should refine against source evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

KEY_PATTERNS = {
    "l1_kv_residency_across_g": ["l1", "resident", "residency", "across_g", "reuse", "kv_outer_g_inner", "k_tile", "v_tile"],
    "l1_partition_policy": ["l1_partition", "kv_split", "kv_pingpong", "k_resident_v_stream", "l1 capacity"],
    "split_kv_lse_merge": ["split_kv", "partial_o", "partial_max", "partial_sum", "lse", "merge"],
    "workspace_no_alias_layout": ["workspace", "no_alias", "alias", "offset", "unique_offset"],
    "sparse_window_range_alignment": ["sparse", "causal", "band", "prefix", "s2_start", "s2_end", "align"],
    "bmm1_vec1_bmm2_vec2_pipeline": ["bmm1", "vec1", "bmm2", "vec2", "pipeline", "waitflag", "setflag"],
    "decode_kv_streaming_loop": ["decode", "kv_block", "kv cache", "paged", "block_table", "q_len"],
    "scalar_offset_hoist": ["scalar", "hoist", "offset", "div", "mod", "precompute"],
    "tail_duplicate_mask": ["tail", "duplicate", "mask", "alignment"],
    "event_wait_flag_dependency": ["event", "wait", "flag", "dependency", "mte3_mte2"],
}

MODULES = {
    "kernel": "Describe operator family, profile, backend, and template selection.",
    "target": "Describe chip resources such as core count, UB/L1/L0 size, and alignment defaults.",
    "features": "Describe implementation mode, dtype, layout, mask/dropout/pse flags, and template traits.",
    "interface": "Describe Q/K/V/O, masks, sequence lengths, workspace, tilingData, and pipe arguments.",
    "shape": "Describe B/S1/S2/N/G/D, varlen, head grouping, and derived axis semantics.",
    "layout": "Describe GM/cache/local tensor layout and format conversions.",
    "tiling": "Describe S1/S2/KV block sizes, base M/N, N ratio, and alignment candidates.",
    "core_mapping": "Describe blockIdx to batch/head/group/S1/KV-split logical-axis mapping.",
    "memory": "Describe GM/UB/L1/L0 buffers, DataCopy, lifetime, and memory-space roles.",
    "l1_partition": "Describe L1 split policy, K/V/scratch regions, ping-pong, and capacity accounting.",
    "l1_residency": "Describe K/V tile residency scope, reuse, prefetch, and eviction policy.",
    "workspace": "Describe GM workspace layout, partial results, LSE states, and no-alias index rules.",
    "pipeline": "Describe BMM/vector/MTE stages, ring depth, event/wait dependency, and fixed variants.",
    "decode": "Describe FlashDecode KV streaming, paged/block-table cache, loop order, split-KV, and merge.",
    "sparse_window": "Describe causal/band/prefix window rules and S2 range alignment.",
    "compute": "Describe online softmax, LSE state, scalar policy, dtype/precision rules.",
    "tail_policy": "Describe tail block, duplicate mask, and alignment behavior.",
    "search": "Describe searchable knobs, transforms, objectives, and budget.",
    "lowering": "Describe template backend, lowering passes, patch points, and output artifacts.",
}

FIELD_TEMPLATES = {
    "tiling": {
        "s1_base": {"type": "int", "candidates": [32, 64, 128], "searchable": True, "editable_policy": "searchable"},
        "s2_base": {"type": "int", "candidates": [64, 128, 256], "searchable": True, "editable_policy": "searchable"},
        "kv_block": {"type": "int", "candidates": [64, 128, 256, 512], "searchable": True, "editable_policy": "searchable"},
        "align_to": {"type": "int", "default": 8, "searchable": False, "editable_policy": "configurable"},
    },
    "decode": {
        "loop_order": {"type": "enum", "enum": ["g_outer_kv_inner", "kv_outer_g_inner"], "searchable": True, "editable_policy": "configurable"},
        "kv_cache_layout": {"type": "enum", "enum": ["contiguous", "paged", "block_table", "tnd", "bnsd"], "searchable": False, "editable_policy": "configurable"},
        "split_kv": {"type": "object", "searchable": True, "editable_policy": "configurable"},
    },
    "l1_partition": {
        "policy": {"type": "enum", "enum": ["k_only", "v_only", "kv_split", "kv_pingpong", "k_resident_v_stream", "shared_pool"], "searchable": True, "editable_policy": "configurable"},
        "regions": {"type": "list", "searchable": False, "editable_policy": "configurable"},
    },
    "l1_residency": {
        "enabled": {"type": "bool", "default": False, "searchable": True, "editable_policy": "configurable"},
        "objects": {"type": "list", "searchable": True, "editable_policy": "configurable"},
        "prefetch_distance": {"type": "int", "candidates": [0, 1, 2], "searchable": True, "editable_policy": "searchable"},
    },
    "workspace": {
        "layout": {"type": "list", "searchable": False, "editable_policy": "configurable"},
        "no_alias": {"type": "bool", "default": True, "searchable": False, "editable_policy": "fixed"},
    },
    "pipeline": {
        "kind": {"type": "enum", "enum": ["fa_forward_ring_pipeline", "decode_kv_streaming_pipeline"], "searchable": False, "editable_policy": "configurable"},
        "ring_depth": {"type": "int", "candidates": [2, 3], "searchable": True, "editable_policy": "searchable"},
        "events": {"type": "list", "searchable": False, "editable_policy": "forbidden"},
    },
    "sparse_window": {
        "mode": {"type": "enum", "enum": ["full", "causal", "right_down_causal", "band", "prefix"], "searchable": False, "editable_policy": "configurable"},
        "align_to": {"type": "int", "default": 8, "searchable": False, "editable_policy": "fixed"},
    },
    "compute": {
        "online_softmax": {"type": "object", "searchable": False, "editable_policy": "fixed"},
        "scalar_policy": {"type": "enum", "enum": ["baseline", "hoist_loop_invariant", "precompute_offset"], "searchable": True, "editable_policy": "searchable"},
    },
}

VALIDATORS = {
    "ub_capacity": ("memory", "estimated_ub_usage(memory, tiling, pipeline) <= target.ub_size"),
    "l1_capacity": ("l1_partition", "sum(enabled_l1_regions.size_expr) <= target.l1_size"),
    "workspace_no_alias": ("workspace", "unique_offset(workspace.layout)"),
    "sparse_window_alignment": ("sparse_window", "s2_start % sparse_window.align_to == 0 and s2_end % sparse_window.align_to == 0"),
    "split_kv_lse_merge_valid": ("decode", "split_kv.enabled implies split_kv.merge.method == online_lse_merge"),
    "event_dependency_valid": ("pipeline", "pipeline.events chosen_from_fixed_valid_variants"),
    "l1_residency_loop_order": ("l1_residency", "residency_scope == across_g implies decode.loop_order == kv_outer_g_inner"),
}

LOWERING = {
    "LowerTiling": (["tiling", "target", "features"], ["host tiling fields", "constexpr constants"], ["host_tiling", "ComputeConstexpr"]),
    "LowerCoreMapping": (["core_mapping", "shape", "tiling"], ["logical axis mapping"], ["ComputeAxisIdx", "Process loop header"]),
    "LowerSparseWindow": (["sparse_window", "shape", "features"], ["s2_start/s2_end expressions"], ["GetS2LoopRange"]),
    "LowerL1Partition": (["l1_partition", "target", "decode", "tiling"], ["L1 regions", "TPipe/TBuf allocation"], ["InitBuffer"]),
    "LowerL1Residency": (["l1_residency", "l1_partition", "decode.loop_order"], ["DataCopy placement", "eviction points"], ["Process", "LoadKvTile"]),
    "LowerDecodeLoopNest": (["decode", "core_mapping", "l1_residency"], ["KV/group/split loops"], ["Process"]),
    "LowerWorkspaceLayout": (["workspace", "decode.split_kv", "shape"], ["workspace offset functions"], ["CalcWorkspaceOffset", "CalcAccumOffset"]),
    "LowerPipeline": (["pipeline", "memory", "compute"], ["stage schedule", "event variants"], ["Process", "pipeline helpers"]),
}


def read_all_text(root: Path) -> str:
    parts: List[str] = []
    if not root.exists():
        return ""
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json", ".md", ".txt"}:
            try:
                parts.append(f"\n\n# FILE: {path}\n" + path.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
    return "\n".join(parts)


def detect_patterns(text: str) -> Dict[str, int]:
    lower = text.lower()
    scores: Dict[str, int] = {}
    for pid, kws in KEY_PATTERNS.items():
        scores[pid] = sum(1 for kw in kws if kw.lower() in lower)
    return scores


def ydump(obj, indent=0) -> str:
    """Tiny YAML-ish dumper for simple dict/list scalars."""
    sp = "  " * indent
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{sp}{k}:")
                lines.append(ydump(v, indent + 1))
            else:
                lines.append(f"{sp}{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, str) else str(v).lower() if isinstance(v, bool) else v}")
        return "\n".join(lines)
    if isinstance(obj, list):
        lines = []
        for item in obj:
            if isinstance(item, dict):
                lines.append(f"{sp}-")
                lines.append(ydump(item, indent + 1))
            else:
                lines.append(f"{sp}- {json.dumps(item, ensure_ascii=False) if isinstance(item, str) else item}")
        return "\n".join(lines)
    return f"{sp}{obj}"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def canonical_optimizations(scores: Dict[str, int]) -> List[dict]:
    selected = [pid for pid, score in scores.items() if score > 0]
    if not selected:
        selected = list(KEY_PATTERNS.keys())[:6]
    result = []
    for pid in selected:
        modules = []
        if "l1" in pid:
            modules += ["l1_partition", "l1_residency", "decode"]
        if "split_kv" in pid:
            modules += ["decode", "workspace", "compute"]
        if "workspace" in pid:
            modules += ["workspace"]
        if "sparse" in pid:
            modules += ["sparse_window", "tiling"]
        if "pipeline" in pid or "event" in pid:
            modules += ["pipeline"]
        if "decode" in pid:
            modules += ["decode", "l1_residency"]
        if "scalar" in pid:
            modules += ["compute"]
        if "tail" in pid:
            modules += ["tail_policy"]
        modules = sorted(set(modules or ["tiling", "memory"]))
        result.append({
            "id": pid,
            "aliases": [],
            "intent": ["derived from Stage 1 optimization cards", "needs manual refinement against source evidence"],
            "applies_to": ["fa_forward", "flash_decode", "sfa"],
            "preconditions": ["see Stage 1 cards"],
            "risks": ["needs Stage 1 risk mapping"],
            "required_dsl_modules": modules,
            "suggested_fields": [],
            "searchable_knobs": [],
            "validators": [],
            "lowering_passes": [],
            "source_evidence": ["needs evidence mapping from stage1_outputs/evidence"],
        })
    return result


def module_items(canon: List[dict]) -> List[dict]:
    module_to_cards: Dict[str, List[str]] = {m: [] for m in MODULES}
    for item in canon:
        for m in item.get("required_dsl_modules", []):
            module_to_cards.setdefault(m, []).append(item["id"])
    items = []
    for name, resp in MODULES.items():
        fields = list(FIELD_TEMPLATES.get(name, {}).keys())
        validators = [v for v, (mod, _) in VALIDATORS.items() if mod == name]
        passes = [p for p, (consumes, _, _) in LOWERING.items() if name in [c.split('.')[0] for c in consumes]]
        items.append({
            "name": name,
            "responsibility": resp,
            "profile_scope": ["all"],
            "source_cards": module_to_cards.get(name, []),
            "core_fields": fields,
            "searchable_fields": [f for f, spec in FIELD_TEMPLATES.get(name, {}).items() if spec.get("searchable")],
            "hard_validators": validators,
            "lowering_passes": passes,
        })
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="stage1_outputs")
    parser.add_argument("--output", default="stage2_outputs")
    args = parser.parse_args()

    in_dir = Path(args.input)
    out = Path(args.output)
    text = read_all_text(in_dir)
    scores = detect_patterns(text)
    canon = canonical_optimizations(scores)
    modules = module_items(canon)

    write(out / "ontology" / "canonical_optimizations.yaml", ydump(canon))
    write(out / "ontology" / "modules.yaml", ydump(modules))

    # Card-to-module matrix
    matrix = ["# Card to Module Matrix", "", "| Card | Modules | Evidence status |", "|---|---|---|"]
    for c in canon:
        matrix.append(f"| `{c['id']}` | {', '.join(c['required_dsl_modules'])} | needs review |")
    write(out / "ontology" / "card_to_module_matrix.md", "\n".join(matrix))

    # Field policy
    policies = {"searchable": [], "configurable": [], "fixed": [], "forbidden": []}
    for mod, fields in FIELD_TEMPLATES.items():
        for fname, spec in fields.items():
            policies.setdefault(spec.get("editable_policy", "fixed"), []).append(f"{mod}.{fname}")
    write(out / "ontology" / "field_policy.yaml", ydump(policies))

    # Main schema
    write(out / "schema" / "atdsl.schema.yaml", ydump({
        "version": "0.2",
        "kind": "ascend.attention.dsl_schema",
        "modules": list(MODULES.keys()),
        "searchable_fields": policies.get("searchable", []),
        "readonly_fields": policies.get("fixed", []) + policies.get("forbidden", []),
        "validators": list(VALIDATORS.keys()),
        "lowering_passes": list(LOWERING.keys()),
    }))

    # Module schemas
    for mod in MODULES:
        fields = FIELD_TEMPLATES.get(mod, {
            "enabled": {"type": "bool", "default": True, "searchable": False, "editable_policy": "fixed"},
        })
        enriched = {}
        for fname, spec in fields.items():
            enriched[fname] = dict(spec)
            enriched[fname].setdefault("source_cards", [c["id"] for c in canon if mod in c.get("required_dsl_modules", [])])
            enriched[fname].setdefault("source_evidence", ["needs evidence mapping"])
            enriched[fname].setdefault("related_validators", [v for v, (m, _) in VALIDATORS.items() if m == mod])
            enriched[fname].setdefault("lowering_consumers", [p for p, (consumes, _, _) in LOWERING.items() if mod in [x.split('.')[0] for x in consumes]])
        write(out / "schema" / "modules" / f"{mod}.schema.yaml", ydump({mod: enriched}))

    # Validators
    for name, (mod, expr) in VALIDATORS.items():
        write(out / "validators_spec" / f"{name}.yaml", ydump({
            "name": name,
            "module": mod,
            "severity": "hard",
            "inputs": [mod, "target", "shape", "tiling"],
            "expr": expr,
            "error_message": f"{name} failed",
            "related_risks": ["correctness_or_compile_failure"],
            "source_cards": [c["id"] for c in canon if mod in c.get("required_dsl_modules", [])],
            "source_evidence": ["needs evidence mapping"],
        }))

    # Lowering specs
    for name, (consumes, emits, patch_points) in LOWERING.items():
        write(out / "lowering_spec" / f"{name}.yaml", ydump({
            "name": name,
            "consumes": consumes,
            "emits": emits,
            "patch_points": patch_points,
            "pre_validators": list(VALIDATORS.keys()),
            "post_validators": ["compile_success", "golden_correctness"],
            "editable_policy": "limited_variants" if name == "LowerPipeline" else "template_or_patch_point",
            "source_cards": [c["id"] for c in canon],
        }))

    # Shadow examples
    fa = {
        "version": "0.2",
        "kind": "ascend.attention.shadow",
        "kernel": {"family": "flash_attention", "profile": "fa_forward", "template": "fa_forward_s1s2_pipeline"},
        "tiling": {"s1_base": 64, "s2_base": 128, "align_to": 8},
        "pipeline": {"kind": "fa_forward_ring_pipeline", "ring_depth": 3, "stages": ["bmm1_qk", "vec1_softmax", "bmm2_pv", "vec2_store"]},
        "sparse_window": {"mode": "causal", "align_to": 8},
        "workspace": {"no_alias": True},
    }
    dec = {
        "version": "0.2",
        "kind": "ascend.attention.shadow",
        "kernel": {"family": "flash_decode", "profile": "decode", "template": "flash_decode_kv_stream_l1_resident"},
        "decode": {"loop_order": "kv_outer_g_inner", "kv_block": 128, "kv_cache_layout": "paged", "split_kv": {"enabled": True, "num_splits": 8, "merge": {"method": "online_lse_merge"}}},
        "l1_partition": {"policy": "k_resident_v_stream"},
        "l1_residency": {"enabled": True, "objects": [{"name": "k_tile", "residency_scope": "across_g", "eviction": "after_all_g_for_this_kv_block"}]},
        "workspace": {"layout": ["partial_o", "partial_max", "partial_sum"], "no_alias": True},
        "constraints": ["l1_capacity", "l1_residency_loop_order", "split_kv_lse_merge_valid", "workspace_no_alias"],
    }
    write(out / "examples" / "fa_forward_shadow.yaml", ydump(fa))
    write(out / "examples" / "flash_decode_shadow.yaml", ydump(dec))
    write(out / "examples" / "sfa_shadow.yaml", ydump({"version": "0.2", "kind": "ascend.attention.shadow", "kernel": {"family": "sparse_flash_attention", "profile": "sfa", "template": "needs_refinement"}, "sparse_window": {"mode": "band", "align_to": 8}}))

    # Review
    write(out / "review" / "schema_review.md", """# Stage 2 Schema Review

This is a generated scaffold. Codex must refine it against Stage 1 source evidence.

## Review checklist

- [ ] Every canonical optimization has source evidence.
- [ ] Every important field has source evidence or `needs_evidence: true`.
- [ ] Every high-risk field has a validator.
- [ ] Every searchable field has candidates/range.
- [ ] Shadow DSL examples express at least two mature kernels.
- [ ] Event schedules are fixed or limited variants.
- [ ] L1 residency has L1 capacity and loop-order validators.
- [ ] split-KV has partial workspace and LSE merge validators.
""")

    coverage = ["# Stage 2 Coverage Matrix", "", "| Area | Status | Notes |", "|---|---|---|"]
    for area in ["tiling", "core_mapping", "pipeline", "L1 partition", "L1 residency", "decode", "workspace", "sparse window", "compute", "tail policy"]:
        coverage.append(f"| {area} | scaffolded | refine against Stage 1 evidence |")
    write(out / "review" / "coverage_matrix.md", "\n".join(coverage))

    write(out / "review" / "missing_fields.md", """# Missing or Weak Fields

Generated scaffold defaults to conservative fields. Codex should inspect Stage 1 artifacts and add or remove fields based on evidence.

Common gaps to check:

- exact L1 region size expressions
- exact workspace offset index dimensions
- exact event/wait variants from mature code
- exact host tiling fields
- exact sparse window modes supported by source code
- exact split-KV merge stage: same kernel vs separate kernel
""")

    quality = {
        "overall_status": "warn",
        "scores": {
            "card_to_module_coverage": 12,
            "field_evidence": 8,
            "searchable_knob_quality": 10,
            "validator_coverage": 14,
            "lowering_spec_clarity": 8,
            "shadow_dsl_coverage": 8,
        },
        "hard_failures": ["source evidence requires manual review"],
        "next_actions": ["refine generated files against Stage 1 evidence", "run check_stage2_quality.py"],
    }
    write(out / "review" / "quality_gate.json", json.dumps(quality, indent=2, ensure_ascii=False))

    print(f"Created Stage 2 scaffold in {out}")


if __name__ == "__main__":
    main()
