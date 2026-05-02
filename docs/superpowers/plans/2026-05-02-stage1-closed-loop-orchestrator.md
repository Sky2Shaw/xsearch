# Stage1 Closed-Loop Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Codex skill that runs a bounded, isolated Stage 1 extract-review-reextract loop for AscendC attention operator artifacts.

**Architecture:** Add a third skill, `stage1-closed-loop-orchestrator`, that coordinates the existing extractor and scorer skills without merging their responsibilities. Deterministic Python scripts manage loop directories, round manifests, review sanitization, artifact copying, and stop-condition checks; model judgement remains in fresh isolated Codex subagents at runtime.

**Tech Stack:** Codex skill folder format, Markdown references, Python 3 standard library scripts, JSON-compatible YAML files, `unittest` for script tests.

---

## Scope Check

This is one cohesive subsystem: a new orchestration skill plus deterministic helper scripts. It does not implement a daemon, an external Codex API wrapper, or the extractor/scorer model steps themselves.

The implementation must preserve the design constraint that extractor and scorer do not share conversation context. Scripts only handle files and structured data; they do not assign semantic review scores.

## File Structure

- Create: `skills/stage1-closed-loop-orchestrator/SKILL.md`
  - Responsibility: concise skill entrypoint, invocation contract, isolation rules, final response shape.
- Create: `skills/stage1-closed-loop-orchestrator/agents/openai.yaml`
  - Responsibility: Codex UI metadata and default prompt.
- Create: `skills/stage1-closed-loop-orchestrator/references/workflow.md`
  - Responsibility: end-to-end loop workflow and Codex subagent dispatch rules.
- Create: `skills/stage1-closed-loop-orchestrator/references/isolation-policy.md`
  - Responsibility: allowed and forbidden context flow for extractor, scorer, and orchestrator.
- Create: `skills/stage1-closed-loop-orchestrator/references/schemas.md`
  - Responsibility: JSON-compatible YAML schemas for manifest, round summary, re-extraction request, stop decision.
- Create: `skills/stage1-closed-loop-orchestrator/references/prompts.md`
  - Responsibility: reusable subagent prompt templates that keep extractor and scorer air-gapped.
- Create: `skills/stage1-closed-loop-orchestrator/scripts/init_loop.py`
  - Responsibility: initialize `.xperf_atdsl_loop/`, write `run_manifest.yaml`, create round 1 directories.
- Create: `skills/stage1-closed-loop-orchestrator/scripts/prepare_next_round.py`
  - Responsibility: copy or reference prior extraction artifacts and prepare next round directories.
- Create: `skills/stage1-closed-loop-orchestrator/scripts/sanitize_review_findings.py`
  - Responsibility: convert structured scorer outputs into narrow `reextraction_request.yaml` without Markdown rationale.
- Create: `skills/stage1-closed-loop-orchestrator/scripts/check_stop_conditions.py`
  - Responsibility: evaluate gate/readiness/round-delta status and write `round_summary.yaml`.
- Create: `skills/stage1-closed-loop-orchestrator/tests/test_init_loop.py`
  - Responsibility: tests for loop initialization.
- Create: `skills/stage1-closed-loop-orchestrator/tests/test_prepare_next_round.py`
  - Responsibility: tests for artifact copying and next-round context.
- Create: `skills/stage1-closed-loop-orchestrator/tests/test_sanitize_review_findings.py`
  - Responsibility: tests that sanitized requests contain only allowed structured facts.
- Create: `skills/stage1-closed-loop-orchestrator/tests/test_check_stop_conditions.py`
  - Responsibility: tests for success, no-improvement, max-round, repeated-blocker, and source-unavailable decisions.

---

### Task 1: Create Skill Skeleton And References

**Files:**
- Create: `skills/stage1-closed-loop-orchestrator/SKILL.md`
- Create: `skills/stage1-closed-loop-orchestrator/agents/openai.yaml`
- Create: `skills/stage1-closed-loop-orchestrator/references/workflow.md`
- Create: `skills/stage1-closed-loop-orchestrator/references/isolation-policy.md`
- Create: `skills/stage1-closed-loop-orchestrator/references/schemas.md`
- Create: `skills/stage1-closed-loop-orchestrator/references/prompts.md`

- [ ] **Step 1: Create directories**

Run:

```bash
mkdir -p skills/stage1-closed-loop-orchestrator/{agents,references,scripts,tests}
```

Expected: command exits with status `0`.

- [ ] **Step 2: Write `SKILL.md`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/SKILL.md`:

```markdown
---
name: stage1-closed-loop-orchestrator
description: Orchestrate isolated Stage 1 extraction and scoring loops for AscendC attention-like operator artifacts. Use when Codex should run extractor and scorer as separate fresh subagents, sanitize review findings into narrow re-extraction requests, and stop when Stage 2 readiness gates pass or the loop stops improving.
---

# Stage1 Closed-Loop Orchestrator

Use this skill to run a bounded extraction-review-reextraction loop for AscendC attention-like operators.

This skill coordinates two existing skills:

- `ascend-operator-structure-extractor` produces Stage 1 artifacts.
- `stage1-artifact-scorer` reviews Stage 1 artifacts.

The orchestrator does not extract and does not score. It moves files, starts isolated subagent tasks when the user explicitly requested isolated subagents, sanitizes scorer findings, and decides whether another round should run.

## Required Isolation Rule

Each extractor round must run in a fresh extractor subagent.

Each scorer round must run in a fresh scorer subagent.

Do not fork extractor conversation into scorer. Do not pass scorer reasoning traces into extractor.

Allowed scorer inputs:

- source root
- extraction artifact root
- `stage1_review/evidence_pack.yaml`
- `stage1_review/source_spot_check_plan.yaml`
- high-value artifact files and targeted source snippets selected by the scorer

Allowed extractor inputs after round 1:

- source root
- prior extraction artifacts
- narrow `reextraction_request.yaml`
- extractor skill instructions

Forbidden cross-context inputs:

- extractor conversation
- extractor self-justification
- scorer conversation
- scorer hidden or long-form rationale
- full `score_report.md` as extractor input
- orchestrator opinions about likely fixes

## Workflow

Read:

- `references/workflow.md`
- `references/isolation-policy.md`
- `references/schemas.md`
- `references/prompts.md`

Default loop root:

```text
<source_root>/.xperf_atdsl_loop/
```

Default max rounds: `3`.

Default terminal readiness: `READY_FOR_STAGE2`.

Use deterministic scripts for:

```bash
python3 scripts/init_loop.py --source-root <source_root>
python3 scripts/prepare_next_round.py --loop-root <loop_root> --from-round 1 --to-round 2
python3 scripts/sanitize_review_findings.py --review-dir <review_dir> --output <reextraction_request.yaml>
python3 scripts/check_stop_conditions.py --loop-root <loop_root> --current-round <round>
```

Scripts do not run model judgement. The parent Codex agent must dispatch the extractor and scorer subagents.

## Final Response

After the loop, summarize:

- loop directory
- rounds completed
- final readiness
- final score
- gate results
- unresolved blockers
- final artifact root
- final review report path
- whether human review is needed
```

- [ ] **Step 3: Write `agents/openai.yaml`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/agents/openai.yaml`:

```yaml
interface:
  display_name: "Stage1 Closed-Loop Orchestrator"
  short_description: "Run isolated extraction and scoring loops for Stage 1 artifacts"
  default_prompt: "Use $stage1-closed-loop-orchestrator with isolated subagents on this operator directory."
policy:
  allow_implicit_invocation: true
```

- [ ] **Step 4: Write `references/workflow.md`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/references/workflow.md`:

```markdown
# Workflow

## Round Chain

Every round follows this chain:

```text
source code
  -> fresh extractor subagent
  -> extraction artifacts
  -> stage1-artifact-scorer/scripts/prepare_review_context.py
  -> evidence_pack.yaml
  -> fresh scorer subagent
  -> scorecard.yaml / blocking_findings.yaml / missing_patterns.yaml / stage2_readiness.yaml
  -> sanitize_review_findings.py
  -> reextraction_request.yaml
  -> next fresh extractor subagent
```

## Round 1

1. Run `scripts/init_loop.py`.
2. Dispatch a fresh extractor subagent with source root, output artifact root, and extractor skill instructions.
3. Run `stage1-artifact-scorer/scripts/prepare_review_context.py` against the extraction artifact root.
4. Dispatch a fresh scorer subagent with only source root, artifacts, evidence pack, scorer skill instructions, and source spot-check plan.
5. Run `scripts/check_stop_conditions.py`.

## Later Rounds

1. Run `scripts/sanitize_review_findings.py` on the previous review directory.
2. Run `scripts/prepare_next_round.py`.
3. Dispatch a fresh extractor subagent with source root, previous artifacts, output artifact root, and `reextraction_request.yaml`.
4. Prepare review context again.
5. Dispatch a fresh scorer subagent.
6. Check stop conditions.

## Subagent Dispatch Requirements

The user request must explicitly authorize isolated subagents. If it does not, pause and ask for permission before running the loop.

Use `fork_context=false` when spawning extractor and scorer subagents. Give each subagent only the files and instructions listed in `isolation-policy.md`.

## Stop Policy

Stop successfully when all configured gates pass and readiness is acceptable.

Stop without success when max rounds are reached, improvement stalls, a repeated critical blocker remains, source evidence is unavailable, or a contradiction persists without new source evidence.
```

- [ ] **Step 5: Write `references/isolation-policy.md`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/references/isolation-policy.md`:

```markdown
# Isolation Policy

## Purpose

The loop must avoid both directions of context contamination:

1. Extractor context must not bias scorer judgement.
2. Scorer reasoning must not teach the extractor to game the score.

This is Codex workflow context isolation. It does not claim model-weight-level isolation.

## Extractor Inputs

Allowed:

- source root
- current or previous extraction artifact root
- narrow `reextraction_request.yaml`
- extractor skill instructions and references

Forbidden:

- scorer subagent conversation
- full scorer Markdown report as prompt context
- scorer hidden or long-form rationale
- score weights as optimization strategy
- prior extractor conversation, except through artifacts on disk

## Scorer Inputs

Allowed:

- source root
- extraction artifact root
- `stage1_review/evidence_pack.yaml`
- `stage1_review/source_spot_check_plan.yaml`
- high-value artifacts referenced by the evidence pack
- source snippets selected by scorer for spot checks

Forbidden:

- extractor subagent conversation
- extractor self-justification
- orchestrator opinions about likely fixes
- full previous scorer reports, except compact score deltas for trend comparison

## Sanitizer Rules

`sanitize_review_findings.py` may read machine-readable scorer outputs:

- `scorecard.yaml`
- `blocking_findings.yaml`
- `missing_patterns.yaml`
- `stage2_readiness.yaml`

It must not copy Markdown rationale, hidden reasoning, or prose recommendations into `reextraction_request.yaml`.

## Evidence Classes

Scorer findings must use:

- `verified_against_source`
- `supported_by_artifacts_only`
- `not_verifiable`
- `contradicted_or_suspicious`

High accuracy requires `verified_against_source`.
```

- [ ] **Step 6: Write `references/schemas.md`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/references/schemas.md`:

```markdown
# Schemas

All helper scripts emit JSON-compatible YAML by writing formatted JSON text to `.yaml` files. This keeps shell tooling simple and avoids requiring PyYAML.

## run_manifest.yaml

```yaml
run_id: string
source_root: string
loop_root: string
max_rounds: integer
acceptable_readiness:
  - READY_FOR_STAGE2
copy_mode: copy | reference
created_at: string
rounds:
  - round: 1
    extraction_dir: string
    review_dir: string
    status: initialized | running | complete
```

## reextraction_request.yaml

```yaml
reextraction_request:
  run_id: string
  round: integer
  source_root: string
  previous_artifact_root: string
  output_artifact_root: string
  required_fixes:
    - id: string
      severity: blocking | major | minor
      type: string
      dimension: string
      target_files:
        - string
      target_symbols:
        - string
      required_artifacts:
        - string
      required_evidence:
        - file
        - function
        - line_range
        - observed_behavior
      acceptance_checks:
        - string
      evidence_class: string
  forbidden_context:
    - extractor_conversation
    - scorer_reasoning_trace
    - full_score_report
```

## round_summary.yaml

```yaml
round_summary:
  run_id: string
  round: integer
  status: continue | success | needs_human_review | max_rounds_reached | no_improvement | repeated_blocker | source_unavailable
  readiness: string
  total_score: integer
  gates_passed: boolean
  blocker_count: integer
  unresolved_blockers:
    - string
  next_action: string
```
```

- [ ] **Step 7: Write `references/prompts.md`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/references/prompts.md`:

```markdown
# Prompts

## Extractor Round 1 Prompt

Use `$ascend-operator-structure-extractor` on the provided source root.

Write artifacts to the specified extraction directory. Do not review or score your own output.

You may read:

- source root
- extractor skill instructions

You may not read scorer reports, scorer conversations, or prior reviewer rationale.

## Extractor Re-Extraction Prompt

Use `$ascend-operator-structure-extractor` to improve the existing Stage 1 artifacts.

You may read:

- source root
- previous extraction artifact root
- output extraction artifact root
- `reextraction_request.yaml`

Only address the structured gaps in `reextraction_request.yaml`. Add source-backed evidence. Do not read full scorer reports.

## Scorer Prompt

Use `$stage1-artifact-scorer` to review the extraction artifacts.

You may read:

- source root
- extraction artifact root
- `stage1_review/evidence_pack.yaml`
- `stage1_review/source_spot_check_plan.yaml`
- source files selected for spot checks

You may not read extractor conversation or extractor self-justification. Treat artifacts as claims and verify critical claims against source code.

Write the standard scorer outputs under the review directory.
```

- [ ] **Step 8: Verify docs mention the isolation boundary**

Run:

```bash
rg -n "fresh|isolated|Forbidden|fork_context|scorer reasoning|extractor conversation" skills/stage1-closed-loop-orchestrator
```

Expected: output includes matches in `SKILL.md`, `workflow.md`, `isolation-policy.md`, and `prompts.md`.

- [ ] **Step 9: Commit skeleton and references**

Run:

```bash
git add skills/stage1-closed-loop-orchestrator/SKILL.md skills/stage1-closed-loop-orchestrator/agents/openai.yaml skills/stage1-closed-loop-orchestrator/references
git commit -m "Add stage1 closed-loop orchestrator skill docs"
```

Expected: commit succeeds and includes only the new skill docs.

---

### Task 2: Implement Loop Initialization

**Files:**
- Create: `skills/stage1-closed-loop-orchestrator/tests/test_init_loop.py`
- Create: `skills/stage1-closed-loop-orchestrator/scripts/init_loop.py`

- [ ] **Step 1: Write failing tests**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/tests/test_init_loop.py`:

```python
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "init_loop.py"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class InitLoopTests(unittest.TestCase):
    def test_initializes_default_loop_root_and_round_one(self):
        with TemporaryDirectory() as td:
            source = Path(td) / "operator"
            source.mkdir()

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--source-root", str(source), "--max-rounds", "4"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            loop_root = source / ".xperf_atdsl_loop"
            self.assertEqual(Path(payload["loop_root"]), loop_root)
            self.assertTrue((loop_root / "round_001" / "extraction").is_dir())
            self.assertTrue((loop_root / "round_001" / "review").is_dir())
            manifest = load_json(loop_root / "run_manifest.yaml")
            self.assertEqual(manifest["source_root"], str(source.resolve()))
            self.assertEqual(manifest["max_rounds"], 4)
            self.assertEqual(manifest["rounds"][0]["round"], 1)
            self.assertEqual(manifest["rounds"][0]["status"], "initialized")

    def test_rejects_missing_source_root(self):
        with TemporaryDirectory() as td:
            missing = Path(td) / "missing"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--source-root", str(missing)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("source root must exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
python3 -m unittest skills/stage1-closed-loop-orchestrator/tests/test_init_loop.py -v
```

Expected: tests fail because `init_loop.py` does not exist.

- [ ] **Step 3: Implement `init_loop.py`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/scripts/init_loop.py`:

```python
#!/usr/bin/env python3
"""Initialize a Stage 1 closed-loop orchestration workspace."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize Stage 1 loop workspace")
    parser.add_argument("--source-root", required=True, help="Operator source directory")
    parser.add_argument("--loop-root", help="Loop output root, default: <source-root>/.xperf_atdsl_loop")
    parser.add_argument("--max-rounds", type=int, default=3, help="Maximum extraction/review rounds")
    parser.add_argument(
        "--acceptable-readiness",
        action="append",
        default=None,
        help="Readiness value accepted as terminal success; may be repeated",
    )
    parser.add_argument(
        "--copy-mode",
        choices=["copy", "reference"],
        default="copy",
        help="Whether later rounds copy previous artifacts or reference them",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def round_record(loop_root: Path, number: int) -> dict:
    round_dir = loop_root / f"round_{number:03d}"
    extraction_dir = round_dir / "extraction"
    review_dir = round_dir / "review"
    extraction_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    return {
        "round": number,
        "round_dir": str(round_dir),
        "extraction_dir": str(extraction_dir),
        "review_dir": str(review_dir),
        "status": "initialized",
    }


def write_json_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_manifest(args: argparse.Namespace, source_root: Path, loop_root: Path) -> dict:
    readiness = args.acceptable_readiness or ["READY_FOR_STAGE2"]
    manifest = {
        "run_id": f"stage1-loop-{uuid4().hex[:12]}",
        "source_root": str(source_root),
        "loop_root": str(loop_root),
        "max_rounds": args.max_rounds,
        "acceptable_readiness": readiness,
        "copy_mode": args.copy_mode,
        "created_at": utc_now(),
        "rounds": [round_record(loop_root, 1)],
    }
    return manifest


def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root).expanduser()
    if not source_root.exists() or not source_root.is_dir():
        print(f"error: source root must exist and be a directory: {source_root}", file=sys.stderr)
        return 2
    if args.max_rounds < 1:
        print("error: --max-rounds must be at least 1", file=sys.stderr)
        return 2

    source_root = source_root.resolve()
    loop_root = Path(args.loop_root).expanduser().resolve() if args.loop_root else source_root / ".xperf_atdsl_loop"
    loop_root.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(args, source_root, loop_root)
    manifest_path = loop_root / "run_manifest.yaml"
    write_json_yaml(manifest_path, manifest)

    print(json.dumps({"loop_root": str(loop_root), "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and confirm pass**

Run:

```bash
python3 -m unittest skills/stage1-closed-loop-orchestrator/tests/test_init_loop.py -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 5: Commit loop initialization**

Run:

```bash
git add skills/stage1-closed-loop-orchestrator/scripts/init_loop.py skills/stage1-closed-loop-orchestrator/tests/test_init_loop.py
git commit -m "Add stage1 loop initialization script"
```

Expected: commit succeeds.

---

### Task 3: Implement Next-Round Preparation

**Files:**
- Create: `skills/stage1-closed-loop-orchestrator/tests/test_prepare_next_round.py`
- Create: `skills/stage1-closed-loop-orchestrator/scripts/prepare_next_round.py`

- [ ] **Step 1: Write failing tests**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/tests/test_prepare_next_round.py`:

```python
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "prepare_next_round.py"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class PrepareNextRoundTests(unittest.TestCase):
    def make_loop(self, root: Path, copy_mode: str = "copy") -> Path:
        loop_root = root / ".xperf_atdsl_loop"
        previous = loop_root / "round_001" / "extraction"
        previous.mkdir(parents=True)
        (previous / "reports").mkdir()
        (previous / "reports" / "function_index.yaml").write_text('{"function_index": {"functions": []}}\n', encoding="utf-8")
        write_json(
            loop_root / "run_manifest.yaml",
            {
                "run_id": "run-1",
                "source_root": str(root / "operator"),
                "loop_root": str(loop_root),
                "max_rounds": 3,
                "acceptable_readiness": ["READY_FOR_STAGE2"],
                "copy_mode": copy_mode,
                "rounds": [
                    {
                        "round": 1,
                        "round_dir": str(loop_root / "round_001"),
                        "extraction_dir": str(previous),
                        "review_dir": str(loop_root / "round_001" / "review"),
                        "status": "complete",
                    }
                ],
            },
        )
        return loop_root

    def test_copy_mode_copies_previous_artifacts_and_updates_manifest(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            loop_root = self.make_loop(root, copy_mode="copy")

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--loop-root", str(loop_root), "--from-round", "1", "--to-round", "2"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            copied = loop_root / "round_002" / "extraction" / "reports" / "function_index.yaml"
            self.assertTrue(copied.exists())
            context = load_json(loop_root / "round_002" / "next_round_context.yaml")
            self.assertEqual(context["from_round"], 1)
            self.assertEqual(context["to_round"], 2)
            manifest = load_json(loop_root / "run_manifest.yaml")
            self.assertEqual(manifest["rounds"][1]["round"], 2)

    def test_rejects_missing_previous_round(self):
        with TemporaryDirectory() as td:
            loop_root = Path(td) / ".xperf_atdsl_loop"
            write_json(loop_root / "run_manifest.yaml", {"rounds": [], "copy_mode": "copy"})

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--loop-root", str(loop_root), "--from-round", "1", "--to-round", "2"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("from round not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
python3 -m unittest skills/stage1-closed-loop-orchestrator/tests/test_prepare_next_round.py -v
```

Expected: tests fail because `prepare_next_round.py` does not exist.

- [ ] **Step 3: Implement `prepare_next_round.py`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/scripts/prepare_next_round.py`:

```python
#!/usr/bin/env python3
"""Prepare directories and context for the next closed-loop round."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare next Stage 1 loop round")
    parser.add_argument("--loop-root", required=True)
    parser.add_argument("--from-round", type=int, required=True)
    parser.add_argument("--to-round", type=int, required=True)
    return parser.parse_args()


def read_json_yaml(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_round(manifest: dict, number: int) -> dict | None:
    for record in manifest.get("rounds", []):
        if record.get("round") == number:
            return record
    return None


def copy_artifacts(previous: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(previous, target)


def upsert_round(manifest: dict, record: dict) -> None:
    rounds = [item for item in manifest.get("rounds", []) if item.get("round") != record["round"]]
    rounds.append(record)
    manifest["rounds"] = sorted(rounds, key=lambda item: item["round"])


def main() -> int:
    args = parse_args()
    if args.to_round <= args.from_round:
        print("error: --to-round must be greater than --from-round", file=sys.stderr)
        return 2

    loop_root = Path(args.loop_root).expanduser().resolve()
    manifest_path = loop_root / "run_manifest.yaml"
    if not manifest_path.exists():
        print(f"error: manifest missing: {manifest_path}", file=sys.stderr)
        return 2

    manifest = read_json_yaml(manifest_path)
    previous_record = find_round(manifest, args.from_round)
    if previous_record is None:
        print(f"error: from round not found: {args.from_round}", file=sys.stderr)
        return 2

    previous_extraction = Path(previous_record["extraction_dir"])
    if not previous_extraction.exists():
        print(f"error: previous extraction missing: {previous_extraction}", file=sys.stderr)
        return 2

    round_dir = loop_root / f"round_{args.to_round:03d}"
    extraction_dir = round_dir / "extraction"
    review_dir = round_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    copy_mode = manifest.get("copy_mode", "copy")
    if copy_mode == "copy":
        copy_artifacts(previous_extraction, extraction_dir)
    else:
        extraction_dir.mkdir(parents=True, exist_ok=True)

    context = {
        "run_id": manifest.get("run_id"),
        "from_round": args.from_round,
        "to_round": args.to_round,
        "source_root": manifest.get("source_root"),
        "previous_artifact_root": str(previous_extraction),
        "output_artifact_root": str(extraction_dir),
        "copy_mode": copy_mode,
    }
    write_json_yaml(round_dir / "next_round_context.yaml", context)

    upsert_round(
        manifest,
        {
            "round": args.to_round,
            "round_dir": str(round_dir),
            "extraction_dir": str(extraction_dir),
            "review_dir": str(review_dir),
            "status": "initialized",
        },
    )
    write_json_yaml(manifest_path, manifest)

    print(json.dumps(context, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and confirm pass**

Run:

```bash
python3 -m unittest skills/stage1-closed-loop-orchestrator/tests/test_prepare_next_round.py -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 5: Commit next-round preparation**

Run:

```bash
git add skills/stage1-closed-loop-orchestrator/scripts/prepare_next_round.py skills/stage1-closed-loop-orchestrator/tests/test_prepare_next_round.py
git commit -m "Add stage1 next-round preparation"
```

Expected: commit succeeds.

---

### Task 4: Implement Review Finding Sanitizer

**Files:**
- Create: `skills/stage1-closed-loop-orchestrator/tests/test_sanitize_review_findings.py`
- Create: `skills/stage1-closed-loop-orchestrator/scripts/sanitize_review_findings.py`

- [ ] **Step 1: Write failing tests**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/tests/test_sanitize_review_findings.py`:

```python
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "sanitize_review_findings.py"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class SanitizeReviewFindingsTests(unittest.TestCase):
    def test_sanitizes_blocking_findings_and_excludes_markdown_rationale(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            review = root / "review"
            output = root / "reextraction_request.yaml"
            write_json(
                review / "scorecard.yaml",
                {
                    "scorecard": {
                        "total": 66,
                        "readiness": "NEEDS_REEXTRACTION",
                        "gates": {"accuracy": {"passed": False}},
                    }
                },
            )
            write_json(
                review / "blocking_findings.yaml",
                {
                    "blocking_findings": [
                        {
                            "id": "missing_flash_decode_merge",
                            "severity": "blocking",
                            "dimension": "coverage",
                            "type": "missing_critical_coverage",
                            "evidence_class": "supported_by_artifacts_only",
                            "source_or_artifact_ref": [
                                {
                                    "path": "op/flash_decode.cpp",
                                    "function": "Merge",
                                    "line_range": {"start": 10, "end": 20},
                                }
                            ],
                            "required_fix": "Deep-extract merge behavior with source evidence.",
                            "reviewer_rationale": "This prose must not be copied.",
                        }
                    ]
                },
            )
            write_json(
                review / "missing_patterns.yaml",
                {
                    "missing_patterns": [
                        {
                            "id": "workspace_offsets",
                            "severity": "major",
                            "target_files": ["op/workspace.cpp"],
                            "required_artifacts": ["constraints/constraints.yaml"],
                            "acceptance_checks": ["workspace offsets cite source lines"],
                        }
                    ]
                },
            )
            (review / "score_report.md").write_text("Long scorer narrative that must not appear.\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--review-dir",
                    str(review),
                    "--output",
                    str(output),
                    "--run-id",
                    "run-1",
                    "--round",
                    "2",
                    "--source-root",
                    "/src",
                    "--previous-artifact-root",
                    "/prev",
                    "--output-artifact-root",
                    "/next",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            request_text = output.read_text(encoding="utf-8")
            self.assertNotIn("Long scorer narrative", request_text)
            self.assertNotIn("reviewer_rationale", request_text)
            self.assertNotIn("This prose must not be copied", request_text)
            request = load_json(output)["reextraction_request"]
            self.assertEqual(request["round"], 2)
            self.assertEqual(request["required_fixes"][0]["id"], "missing_flash_decode_merge")
            self.assertIn("file", request["required_fixes"][0]["required_evidence"])
            self.assertIn("full_score_report", request["forbidden_context"])

    def test_missing_structured_outputs_returns_nonzero(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            review = root / "review"
            review.mkdir()
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--review-dir",
                    str(review),
                    "--output",
                    str(root / "request.yaml"),
                    "--run-id",
                    "run-1",
                    "--round",
                    "2",
                    "--source-root",
                    "/src",
                    "--previous-artifact-root",
                    "/prev",
                    "--output-artifact-root",
                    "/next",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("no structured review findings", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
python3 -m unittest skills/stage1-closed-loop-orchestrator/tests/test_sanitize_review_findings.py -v
```

Expected: tests fail because `sanitize_review_findings.py` does not exist.

- [ ] **Step 3: Implement `sanitize_review_findings.py`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/scripts/sanitize_review_findings.py`:

```python
#!/usr/bin/env python3
"""Convert structured scorer outputs into a narrow re-extraction request."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SAFE_FINDING_KEYS = {
    "id",
    "severity",
    "dimension",
    "type",
    "target_files",
    "target_symbols",
    "required_artifacts",
    "acceptance_checks",
    "evidence_class",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sanitize Stage 1 review findings")
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--previous-artifact-root", required=True)
    parser.add_argument("--output-artifact-root", required=True)
    return parser.parse_args()


def read_json_yaml(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional(path: Path) -> Any:
    if not path.exists():
        return {}
    return read_json_yaml(path)


def write_json_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def refs_to_targets(refs: list[Any]) -> tuple[list[str], list[str]]:
    files: list[str] = []
    symbols: list[str] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        path = ref.get("path")
        function = ref.get("function")
        if isinstance(path, str) and path and path not in files:
            files.append(path)
        if isinstance(function, str) and function and function not in symbols:
            symbols.append(function)
    return files, symbols


def sanitize_structured_finding(finding: dict[str, Any]) -> dict[str, Any]:
    sanitized = {key: finding[key] for key in SAFE_FINDING_KEYS if key in finding}
    refs = as_list(finding.get("source_or_artifact_ref"))
    files, symbols = refs_to_targets(refs)
    existing_files = as_list(sanitized.get("target_files"))
    existing_symbols = as_list(sanitized.get("target_symbols"))
    sanitized["target_files"] = [item for item in existing_files + files if isinstance(item, str)]
    sanitized["target_symbols"] = [item for item in existing_symbols + symbols if isinstance(item, str)]
    if "required_artifacts" not in sanitized:
        sanitized["required_artifacts"] = []
    if "required_evidence" not in sanitized:
        sanitized["required_evidence"] = ["file", "function", "line_range", "observed_behavior"]
    if "acceptance_checks" not in sanitized:
        required_fix = finding.get("required_fix")
        sanitized["acceptance_checks"] = [required_fix] if isinstance(required_fix, str) and required_fix else []
    if "type" not in sanitized:
        sanitized["type"] = sanitized.get("dimension", "review_finding")
    return sanitized


def collect_findings(review_dir: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    blocking = load_optional(review_dir / "blocking_findings.yaml")
    for item in as_list(blocking.get("blocking_findings") if isinstance(blocking, dict) else blocking):
        if isinstance(item, dict):
            findings.append(sanitize_structured_finding(item))
    missing = load_optional(review_dir / "missing_patterns.yaml")
    for item in as_list(missing.get("missing_patterns") if isinstance(missing, dict) else missing):
        if isinstance(item, dict):
            findings.append(sanitize_structured_finding(item))
    return findings


def main() -> int:
    args = parse_args()
    review_dir = Path(args.review_dir).expanduser().resolve()
    findings = collect_findings(review_dir)
    if not findings:
        print(f"error: no structured review findings found in {review_dir}", file=sys.stderr)
        return 2

    request = {
        "reextraction_request": {
            "run_id": args.run_id,
            "round": args.round,
            "source_root": args.source_root,
            "previous_artifact_root": args.previous_artifact_root,
            "output_artifact_root": args.output_artifact_root,
            "required_fixes": findings,
            "forbidden_context": [
                "extractor_conversation",
                "scorer_reasoning_trace",
                "full_score_report",
            ],
        }
    }
    output = Path(args.output).expanduser().resolve()
    write_json_yaml(output, request)
    print(json.dumps({"output": str(output), "required_fix_count": len(findings)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and confirm pass**

Run:

```bash
python3 -m unittest skills/stage1-closed-loop-orchestrator/tests/test_sanitize_review_findings.py -v
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 5: Commit sanitizer**

Run:

```bash
git add skills/stage1-closed-loop-orchestrator/scripts/sanitize_review_findings.py skills/stage1-closed-loop-orchestrator/tests/test_sanitize_review_findings.py
git commit -m "Add stage1 review finding sanitizer"
```

Expected: commit succeeds.

---

### Task 5: Implement Stop-Condition Evaluation

**Files:**
- Create: `skills/stage1-closed-loop-orchestrator/tests/test_check_stop_conditions.py`
- Create: `skills/stage1-closed-loop-orchestrator/scripts/check_stop_conditions.py`

- [ ] **Step 1: Write failing tests**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/tests/test_check_stop_conditions.py`:

```python
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "check_stop_conditions.py"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class CheckStopConditionsTests(unittest.TestCase):
    def make_loop(self, root: Path, max_rounds: int = 3) -> Path:
        loop_root = root / ".xperf_atdsl_loop"
        write_json(
            loop_root / "run_manifest.yaml",
            {
                "run_id": "run-1",
                "source_root": str(root / "operator"),
                "loop_root": str(loop_root),
                "max_rounds": max_rounds,
                "acceptable_readiness": ["READY_FOR_STAGE2"],
                "rounds": [
                    {"round": i, "review_dir": str(loop_root / f"round_{i:03d}" / "review")}
                    for i in range(1, max_rounds + 1)
                ],
            },
        )
        return loop_root

    def write_score(self, loop_root: Path, round_number: int, total: int, readiness: str, gates_passed: bool, blockers: list[str]) -> None:
        review = loop_root / f"round_{round_number:03d}" / "review"
        write_json(
            review / "scorecard.yaml",
            {
                "scorecard": {
                    "total": total,
                    "readiness": readiness,
                    "gates": {
                        "coverage": {"passed": gates_passed},
                        "accuracy": {"passed": gates_passed},
                        "dsl_convertibility": {"passed": gates_passed},
                    },
                }
            },
        )
        write_json(
            review / "blocking_findings.yaml",
            {"blocking_findings": [{"id": blocker, "evidence_class": "verified_against_source"} for blocker in blockers]},
        )

    def run_script(self, loop_root: Path, current_round: int):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--loop-root", str(loop_root), "--current-round", str(current_round)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_success_when_ready_and_gates_pass(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 91, "READY_FOR_STAGE2", True, [])

            result = self.run_script(loop_root, 1)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_001" / "round_summary.yaml")["round_summary"]
            self.assertEqual(summary["status"], "success")
            self.assertTrue(summary["gates_passed"])
            final = load_json(loop_root / "final_readiness.yaml")["final_readiness"]
            self.assertEqual(final["status"], "success")

    def test_no_improvement_after_two_rounds(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 60, "NEEDS_REEXTRACTION", False, ["a", "b"])
            self.write_score(loop_root, 2, 60, "NEEDS_REEXTRACTION", False, ["a", "b"])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")["round_summary"]
            self.assertEqual(summary["status"], "no_improvement")

    def test_max_rounds_has_priority_after_current_round_reaches_limit(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td), max_rounds=2)
            self.write_score(loop_root, 1, 60, "NEEDS_REEXTRACTION", False, ["a"])
            self.write_score(loop_root, 2, 70, "READY_WITH_FIXES", False, ["a"])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")["round_summary"]
            self.assertEqual(summary["status"], "max_rounds_reached")

    def test_source_unavailable_blocks_success(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 88, "READY_FOR_STAGE2", True, ["source_unavailable"])
            write_json(loop_root / "round_001" / "review" / "stage2_readiness.yaml", {"source_available": False})

            result = self.run_script(loop_root, 1)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_001" / "round_summary.yaml")["round_summary"]
            self.assertEqual(summary["status"], "source_unavailable")

    def test_repeated_blocker_when_score_improves_but_same_blocker_remains(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 50, "NEEDS_REEXTRACTION", False, ["same_gap"])
            self.write_score(loop_root, 2, 65, "NEEDS_REEXTRACTION", False, ["same_gap"])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")["round_summary"]
            self.assertEqual(summary["status"], "repeated_blocker")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
python3 -m unittest skills/stage1-closed-loop-orchestrator/tests/test_check_stop_conditions.py -v
```

Expected: tests fail because `check_stop_conditions.py` does not exist.

- [ ] **Step 3: Implement `check_stop_conditions.py`**

Use `apply_patch` to create `skills/stage1-closed-loop-orchestrator/scripts/check_stop_conditions.py`:

```python
#!/usr/bin/env python3
"""Evaluate Stage 1 closed-loop stop conditions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Stage 1 loop stop conditions")
    parser.add_argument("--loop-root", required=True)
    parser.add_argument("--current-round", type=int, required=True)
    return parser.parse_args()


def read_json_yaml(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional(path: Path) -> Any:
    if not path.exists():
        return {}
    return read_json_yaml(path)


def write_json_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def review_dir(loop_root: Path, round_number: int) -> Path:
    return loop_root / f"round_{round_number:03d}" / "review"


def load_score(loop_root: Path, round_number: int) -> dict:
    data = read_json_yaml(review_dir(loop_root, round_number) / "scorecard.yaml")
    return data.get("scorecard", data)


def load_blocker_ids(loop_root: Path, round_number: int) -> list[str]:
    data = load_optional(review_dir(loop_root, round_number) / "blocking_findings.yaml")
    items = data.get("blocking_findings", data if isinstance(data, list) else [])
    ids: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            ids.append(str(item["id"]))
    return ids


def gates_passed(scorecard: dict) -> bool:
    gates = scorecard.get("gates", {})
    if not gates:
        return False
    return all(bool(value.get("passed")) for value in gates.values() if isinstance(value, dict))


def source_unavailable(loop_root: Path, round_number: int) -> bool:
    readiness = load_optional(review_dir(loop_root, round_number) / "stage2_readiness.yaml")
    if isinstance(readiness, dict) and readiness.get("source_available") is False:
        return True
    blockers = set(load_blocker_ids(loop_root, round_number))
    return "source_unavailable" in blockers


def no_improvement(loop_root: Path, current_round: int, current_score: dict, current_blockers: list[str]) -> bool:
    if current_round < 2:
        return False
    previous_score = load_score(loop_root, current_round - 1)
    previous_blockers = load_blocker_ids(loop_root, current_round - 1)
    current_total = int(current_score.get("total", 0))
    previous_total = int(previous_score.get("total", 0))
    return current_total <= previous_total and len(current_blockers) >= len(previous_blockers)


def repeated_blocker(loop_root: Path, current_round: int, current_blockers: list[str]) -> bool:
    if current_round < 2:
        return False
    previous = set(load_blocker_ids(loop_root, current_round - 1))
    return bool(previous.intersection(current_blockers))


def build_summary(loop_root: Path, current_round: int, manifest: dict) -> dict:
    scorecard = load_score(loop_root, current_round)
    blockers = load_blocker_ids(loop_root, current_round)
    readiness = str(scorecard.get("readiness", "UNKNOWN"))
    total = int(scorecard.get("total", 0))
    passed = gates_passed(scorecard)
    acceptable = set(manifest.get("acceptable_readiness") or ["READY_FOR_STAGE2"])
    max_rounds = int(manifest.get("max_rounds", 3))

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
        next_action = "Generate reextraction_request.yaml and run another isolated extractor round."

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


def write_final_readiness(loop_root: Path, summary: dict) -> None:
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


def main() -> int:
    args = parse_args()
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
    summary = build_summary(loop_root, args.current_round, manifest)
    output = loop_root / f"round_{args.current_round:03d}" / "round_summary.yaml"
    write_json_yaml(output, summary)
    write_final_readiness(loop_root, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and confirm pass**

Run:

```bash
python3 -m unittest skills/stage1-closed-loop-orchestrator/tests/test_check_stop_conditions.py -v
```

Expected: `Ran 5 tests` and `OK`.

- [ ] **Step 5: Commit stop-condition evaluator**

Run:

```bash
git add skills/stage1-closed-loop-orchestrator/scripts/check_stop_conditions.py skills/stage1-closed-loop-orchestrator/tests/test_check_stop_conditions.py
git commit -m "Add stage1 loop stop condition checks"
```

Expected: commit succeeds.

---

### Task 6: Run Full Verification And Tighten Docs

**Files:**
- Modify: `skills/stage1-closed-loop-orchestrator/SKILL.md`
- Modify: `skills/stage1-closed-loop-orchestrator/references/workflow.md`
- Modify: `skills/stage1-closed-loop-orchestrator/references/isolation-policy.md`
- Modify: `skills/stage1-closed-loop-orchestrator/references/schemas.md`
- Modify: `skills/stage1-closed-loop-orchestrator/references/prompts.md`

- [ ] **Step 1: Run all orchestrator tests**

Run:

```bash
python3 -m unittest discover -s skills/stage1-closed-loop-orchestrator/tests -v
```

Expected: `Ran 11 tests` and `OK`.

- [ ] **Step 2: Run unresolved-marker and leakage scans**

Run:

```bash
rg -n "T[B]D|T[O]DO|F[I]XME|implement[ ]later|score_report.md as extractor input|reviewer_rationale|Long scorer narrative" skills/stage1-closed-loop-orchestrator/SKILL.md skills/stage1-closed-loop-orchestrator/references skills/stage1-closed-loop-orchestrator/scripts
```

Expected: command exits with status `1`, meaning no matches.

- [ ] **Step 3: Verify scripts are stdlib-only**

Run:

```bash
rg -n "^import |^from " skills/stage1-closed-loop-orchestrator/scripts
```

Expected: imports are only from Python standard library modules used in the plan: `argparse`, `json`, `shutil`, `sys`, `datetime`, `pathlib`, `typing`, and `uuid`.

- [ ] **Step 4: Run a small smoke flow**

Run:

```bash
tmpdir="$(mktemp -d)"
mkdir -p "$tmpdir/operator"
python3 skills/stage1-closed-loop-orchestrator/scripts/init_loop.py --source-root "$tmpdir/operator" --max-rounds 2
mkdir -p "$tmpdir/operator/.xperf_atdsl_loop/round_001/review"
cat > "$tmpdir/operator/.xperf_atdsl_loop/round_001/review/scorecard.yaml" <<'JSON'
{
  "scorecard": {
    "total": 90,
    "readiness": "READY_FOR_STAGE2",
    "gates": {
      "coverage": {"passed": true},
      "accuracy": {"passed": true},
      "dsl_convertibility": {"passed": true}
    }
  }
}
JSON
cat > "$tmpdir/operator/.xperf_atdsl_loop/round_001/review/blocking_findings.yaml" <<'JSON'
{"blocking_findings": []}
JSON
python3 skills/stage1-closed-loop-orchestrator/scripts/check_stop_conditions.py --loop-root "$tmpdir/operator/.xperf_atdsl_loop" --current-round 1
test -f "$tmpdir/operator/.xperf_atdsl_loop/round_001/round_summary.yaml"
```

Expected: final command exits with status `0`, and the printed summary has `"status": "success"`.

- [ ] **Step 5: Validate skill metadata manually**

Run:

```bash
sed -n '1,40p' skills/stage1-closed-loop-orchestrator/SKILL.md
```

Expected: frontmatter has exactly `name` and `description`, followed by the skill body.

- [ ] **Step 6: Commit verification fixes**

If any documentation tightening was needed, commit it:

```bash
git add skills/stage1-closed-loop-orchestrator
git commit -m "Verify stage1 closed-loop orchestrator skill"
```

Expected: commit succeeds if files changed. If no files changed, `git status --short` shows no staged orchestrator changes.

---

## Manual Runtime Handoff

After implementation, the orchestrator can be used in Codex with:

```text
Use $stage1-closed-loop-orchestrator with isolated subagents on <operator_dir>.
```

The parent Codex agent should then:

1. Run `init_loop.py`.
2. Spawn a fresh extractor subagent with only allowed extractor inputs.
3. Run the scorer context preparation script from `stage1-artifact-scorer`.
4. Spawn a fresh scorer subagent with only allowed scorer inputs.
5. Run `check_stop_conditions.py`.
6. If continuing, run `sanitize_review_findings.py`, then `prepare_next_round.py`, then repeat.

## Final Verification

Before claiming completion:

```bash
python3 -m unittest discover -s skills/stage1-closed-loop-orchestrator/tests -v
rg -n "T[B]D|T[O]DO|F[I]XME|implement[ ]later" skills/stage1-closed-loop-orchestrator
git status --short
```

Expected:

- tests pass;
- unresolved-marker scan exits with status `1`;
- git status shows only intended changes or a clean tree after commits.
