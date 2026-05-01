#!/usr/bin/env python3
"""Initialize output directories for Ascend operator extraction."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


STANDARD_DIRS = [
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


def safe_name(value: str) -> str:
    """Return a filesystem-friendly name for generated output roots."""
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    sanitized = sanitized.strip("._-")
    return sanitized or "operator"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize Ascend operator extraction output directories"
    )
    parser.add_argument("--target-dir", required=True, help="Operator source directory")
    parser.add_argument("--output-root", help="Directory where extraction output is created")
    parser.add_argument("--operator-name", help="Operator name for read-only default output")
    parser.add_argument(
        "--read-only-target",
        action="store_true",
        help="Avoid creating output inside the target directory by default",
    )
    return parser.parse_args()


def default_output_root(args: argparse.Namespace, target_dir: Path) -> Path:
    if args.output_root:
        return Path(args.output_root).expanduser()

    if args.read_only_target:
        operator_name = args.operator_name or target_dir.name
        return Path("/tmp") / f"atdsl_extraction_{safe_name(operator_name)}"

    return target_dir / ".xperf_atdsl_extraction"


def main() -> int:
    args = parse_args()
    target_dir = Path(args.target_dir).expanduser().resolve()
    if not target_dir.is_dir():
        print(f"error: --target-dir must exist and be a directory: {target_dir}", file=sys.stderr)
        return 2

    output_root = default_output_root(args, target_dir)
    if args.output_root or not args.read_only_target:
        output_root = output_root.resolve()

    created_dirs = []
    for relative_dir in STANDARD_DIRS:
        directory = output_root / relative_dir
        directory.mkdir(parents=True, exist_ok=True)
        created_dirs.append(str(directory))

    print(
        json.dumps(
            {
                "target_dir": str(target_dir),
                "output_root": str(output_root),
                "created_dirs": created_dirs,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
