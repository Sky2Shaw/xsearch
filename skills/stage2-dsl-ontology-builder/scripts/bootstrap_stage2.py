#!/usr/bin/env python3
"""
DEPRECATED: This script is preserved for backward compatibility.
It now delegates to stage2_parser.py + stage2_synthesizer.py.
Use the new pipeline directly for evidence-driven generation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    print("WARNING: bootstrap_stage2.py is deprecated. Use stage2_parser.py + stage2_synthesizer.py instead.", file=sys.stderr)

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="stage1_outputs")
    parser.add_argument("--output", default="stage2_outputs")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    graph_path = output_dir / ".evidence_graph.json"

    # Run parser
    result = subprocess.run(
        [sys.executable, str(script_dir / "stage2_parser.py"), "--input", str(input_dir), "--output", str(graph_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Parser failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)

    # Run synthesizer
    result = subprocess.run(
        [sys.executable, str(script_dir / "stage2_synthesizer.py"), "--evidence-graph", str(graph_path), "--output", str(output_dir)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Synthesizer failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)

    print(f"Stage 2 scaffold created in {output_dir}")


if __name__ == "__main__":
    main()
