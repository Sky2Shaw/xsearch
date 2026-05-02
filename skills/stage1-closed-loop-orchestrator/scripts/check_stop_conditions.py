#!/usr/bin/env python3
"""Evaluate Stage 1 closed-loop stop conditions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Stage 1 loop stop conditions")
    parser.add_argument("--loop-root", required=True)
    parser.add_argument("--current-round", type=int, required=True)
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


def review_dir(loop_root: Path, round_number: int) -> Path:
    return loop_root / f"round_{round_number:03d}" / "review"


def load_score(loop_root: Path, round_number: int) -> dict[str, Any]:
    data = read_json_yaml(review_dir(loop_root, round_number) / "scorecard.yaml")
    if isinstance(data, dict):
        scorecard = data.get("scorecard", data)
        if isinstance(scorecard, dict):
            return scorecard
    return {}


def load_blocker_ids(loop_root: Path, round_number: int) -> list[str]:
    data = load_optional(review_dir(loop_root, round_number) / "blocking_findings.yaml")
    items = data.get("blocking_findings", data if isinstance(data, list) else [])
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return ids


def gates_passed(scorecard: dict[str, Any]) -> bool:
    gates = scorecard.get("gates", {})
    if not isinstance(gates, dict) or not gates:
        return False
    gate_values = [value for value in gates.values() if isinstance(value, dict)]
    return bool(gate_values) and all(bool(value.get("passed")) for value in gate_values)


def source_unavailable(loop_root: Path, round_number: int) -> bool:
    readiness = load_optional(review_dir(loop_root, round_number) / "stage2_readiness.yaml")
    if isinstance(readiness, dict) and readiness.get("source_available") is False:
        return True
    blockers = set(load_blocker_ids(loop_root, round_number))
    return "source_unavailable" in blockers


def score_total(scorecard: dict[str, Any]) -> int:
    try:
        return int(scorecard.get("total", 0))
    except (TypeError, ValueError):
        return 0


def no_improvement(
    loop_root: Path,
    current_round: int,
    current_score: dict[str, Any],
    current_blockers: list[str],
) -> bool:
    if current_round < 2:
        return False
    previous_score = load_score(loop_root, current_round - 1)
    previous_blockers = load_blocker_ids(loop_root, current_round - 1)
    return score_total(current_score) <= score_total(previous_score) and len(
        current_blockers
    ) >= len(previous_blockers)


def repeated_blocker(
    loop_root: Path, current_round: int, current_blockers: list[str]
) -> bool:
    if current_round < 2:
        return False
    previous = set(load_blocker_ids(loop_root, current_round - 1))
    return bool(previous.intersection(current_blockers))


def build_summary(loop_root: Path, current_round: int, manifest: dict[str, Any]) -> dict[str, Any]:
    scorecard = load_score(loop_root, current_round)
    blockers = load_blocker_ids(loop_root, current_round)
    readiness = str(scorecard.get("readiness", "UNKNOWN"))
    total = score_total(scorecard)
    passed = gates_passed(scorecard)
    acceptable = set(manifest.get("acceptable_readiness") or ["READY_FOR_STAGE2"])
    try:
        max_rounds = int(manifest.get("max_rounds", 3))
    except (TypeError, ValueError):
        max_rounds = 3

    if source_unavailable(loop_root, current_round):
        status = "source_unavailable"
        next_action = "Stop and provide source files or source-root configuration."
    elif passed and readiness in acceptable:
        status = "success"
        next_action = "Stop; artifacts are ready according to configured gates."
    elif current_round >= max_rounds:
        status = "max_rounds_reached"
        next_action = "Stop and request human review of unresolved blockers."
    elif no_improvement(loop_root, current_round, scorecard, blockers):
        status = "no_improvement"
        next_action = "Stop and request human review before another extraction round."
    elif repeated_blocker(loop_root, current_round, blockers):
        status = "repeated_blocker"
        next_action = "Stop if the same blocker repeats after the next targeted fix."
    else:
        status = "continue"
        next_action = (
            "Generate reextraction_request.yaml and run another isolated extractor round."
        )

    return {
        "round_summary": {
            "run_id": manifest.get("run_id"),
            "round": current_round,
            "status": status,
            "readiness": readiness,
            "total_score": total,
            "gates_passed": passed,
            "blocker_count": len(blockers),
            "unresolved_blockers": blockers,
            "next_action": next_action,
        }
    }


def write_final_readiness(loop_root: Path, summary: dict[str, Any]) -> None:
    round_summary = summary["round_summary"]
    if round_summary["status"] == "continue":
        return
    write_json_yaml(
        loop_root / "final_readiness.yaml",
        {
            "final_readiness": {
                "run_id": round_summary["run_id"],
                "round": round_summary["round"],
                "status": round_summary["status"],
                "readiness": round_summary["readiness"],
                "total_score": round_summary["total_score"],
                "gates_passed": round_summary["gates_passed"],
                "unresolved_blockers": round_summary["unresolved_blockers"],
                "human_review_needed": round_summary["status"] not in {"success"},
            }
        },
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    loop_root = Path(args.loop_root).expanduser().resolve()
    manifest_path = loop_root / "run_manifest.yaml"
    if not manifest_path.exists():
        print(f"error: manifest missing: {manifest_path}", file=sys.stderr)
        return 2
    score_path = review_dir(loop_root, args.current_round) / "scorecard.yaml"
    if not score_path.exists():
        print(f"error: scorecard missing: {score_path}", file=sys.stderr)
        return 2

    manifest = read_json_yaml(manifest_path)
    if not isinstance(manifest, dict):
        print("error: manifest must be an object", file=sys.stderr)
        return 2
    summary = build_summary(loop_root, args.current_round, manifest)
    output = loop_root / f"round_{args.current_round:03d}" / "round_summary.yaml"
    write_json_yaml(output, summary)
    write_final_readiness(loop_root, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
