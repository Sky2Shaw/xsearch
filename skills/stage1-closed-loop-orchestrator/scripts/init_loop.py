#!/usr/bin/env python3
import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ACCEPTABLE_READINESS = ["READY_FOR_STAGE2"]


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Initialize a Stage1 closed-loop orchestration run."
    )
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--loop-root")
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--acceptable-readiness", action="append", default=None)
    parser.add_argument("--copy-mode", choices=("copy", "reference"), default="copy")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    source_root = Path(args.source_root)
    if not source_root.is_dir():
        print("source root must exist and be a directory", file=sys.stderr)
        return 2

    if args.max_rounds < 1:
        print("max rounds must be at least 1", file=sys.stderr)
        return 2

    loop_root = Path(args.loop_root) if args.loop_root else source_root / ".xperf_atdsl_loop"
    round_dir = loop_root / "round_001"
    extraction_dir = round_dir / "extraction"
    review_dir = round_dir / "review"

    extraction_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = loop_root / "run_manifest.yaml"
    manifest = {
        "run_id": f"stage1-loop-{secrets.token_hex(6)}",
        "source_root": str(source_root.resolve()),
        "loop_root": str(loop_root),
        "max_rounds": args.max_rounds,
        "acceptable_readiness": args.acceptable_readiness
        or DEFAULT_ACCEPTABLE_READINESS,
        "copy_mode": args.copy_mode,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rounds": [
            {
                "round": 1,
                "round_dir": str(round_dir),
                "extraction_dir": str(extraction_dir),
                "review_dir": str(review_dir),
                "status": "initialized",
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(json.dumps({"loop_root": str(loop_root), "manifest": str(manifest_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
