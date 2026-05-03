#!/usr/bin/env python3
"""
DEPRECATED: This script is preserved for backward compatibility.
It now delegates to stage2_verifier.py.
Use the new verifier directly for semantic quality checks.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    print("WARNING: check_stage2_quality.py is deprecated. Use stage2_verifier.py instead.", file=sys.stderr)

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="stage2_outputs")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    stage2_dir = Path(args.input)
    graph_path = stage2_dir / ".evidence_graph.json"

    result = subprocess.run(
        [sys.executable, str(script_dir / "stage2_verifier.py"), "--evidence-graph", str(graph_path), "--stage2-dir", str(stage2_dir)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
