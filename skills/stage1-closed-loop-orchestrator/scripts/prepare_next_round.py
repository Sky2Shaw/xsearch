#!/usr/bin/env python3
import argparse
import json
import shutil
import sys
from pathlib import Path


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Prepare the next Stage1 closed-loop orchestration round."
    )
    parser.add_argument("--loop-root", required=True)
    parser.add_argument("--from-round", type=int, required=True)
    parser.add_argument("--to-round", type=int, required=True)
    return parser.parse_args(argv)


def write_json(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def absolute_path(path):
    path = Path(path).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path


def main(argv=None):
    args = parse_args(argv)

    loop_root = absolute_path(args.loop_root)
    manifest_path = loop_root / "run_manifest.yaml"
    if not manifest_path.is_file():
        print("run manifest not found", file=sys.stderr)
        return 2

    if args.to_round <= args.from_round:
        print("to-round must be greater than from-round", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rounds = manifest.get("rounds", [])
    previous_round = next(
        (round_record for round_record in rounds if round_record.get("round") == args.from_round),
        None,
    )
    if previous_round is None:
        print("from round not found", file=sys.stderr)
        return 2

    previous_artifact_root = absolute_path(previous_round["extraction_dir"])
    if not previous_artifact_root.is_dir():
        print("previous extraction_dir not found", file=sys.stderr)
        return 2

    copy_mode = manifest.get("copy_mode", "copy")
    round_dir = loop_root / f"round_{args.to_round:03d}"
    output_artifact_root = round_dir / "extraction"
    review_dir = round_dir / "review"

    if copy_mode == "copy":
        if output_artifact_root.exists():
            shutil.rmtree(output_artifact_root)
        shutil.copytree(previous_artifact_root, output_artifact_root)
    else:
        output_artifact_root.mkdir(parents=True, exist_ok=True)

    review_dir.mkdir(parents=True, exist_ok=True)

    context = {
        "run_id": manifest.get("run_id"),
        "from_round": args.from_round,
        "to_round": args.to_round,
        "source_root": str(absolute_path(manifest["source_root"])),
        "previous_artifact_root": str(previous_artifact_root),
        "output_artifact_root": str(output_artifact_root),
        "copy_mode": copy_mode,
    }
    write_json(round_dir / "next_round_context.yaml", context)

    next_round_record = {
        "round": args.to_round,
        "round_dir": str(round_dir),
        "extraction_dir": str(output_artifact_root),
        "review_dir": str(review_dir),
        "status": "initialized",
    }
    updated_rounds = [
        round_record
        for round_record in rounds
        if round_record.get("round") != args.to_round
    ]
    updated_rounds.append(next_round_record)
    manifest["rounds"] = sorted(
        updated_rounds, key=lambda round_record: round_record.get("round", 0)
    )
    write_json(manifest_path, manifest)

    print(json.dumps(context, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
