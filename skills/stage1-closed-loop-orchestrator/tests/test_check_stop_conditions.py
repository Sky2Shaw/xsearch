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
    def make_loop(
        self, root: Path, max_rounds: int = 3, success_score_threshold: int = 85
    ) -> Path:
        loop_root = root / ".xperf_atdsl_loop"
        write_json(
            loop_root / "run_manifest.yaml",
            {
                "run_id": "run-1",
                "source_root": str(root / "operator"),
                "loop_root": str(loop_root),
                "max_rounds": max_rounds,
                "success_score_threshold": success_score_threshold,
                "acceptable_readiness": ["READY_FOR_STAGE2"],
                "rounds": [
                    {
                        "round": i,
                        "review_dir": str(loop_root / f"round_{i:03d}" / "review"),
                    }
                    for i in range(1, max_rounds + 1)
                ],
            },
        )
        return loop_root

    def write_score(
        self,
        loop_root: Path,
        round_number: int,
        total: int,
        readiness: str,
        gates_passed: bool,
        blockers: list[str],
    ) -> None:
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
            {
                "blocking_findings": [
                    {"id": blocker, "evidence_class": "verified_against_source"}
                    for blocker in blockers
                ]
            },
        )

    def run_script(self, loop_root: Path, current_round: int):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--loop-root",
                str(loop_root),
                "--current-round",
                str(current_round),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_first_passing_score_does_not_terminate_success(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 91, "READY_FOR_STAGE2", True, [])

            result = self.run_script(loop_root, 1)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_001" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "continue")
            self.assertTrue(summary["gates_passed"])
            self.assertEqual(summary["success_score_threshold"], 85)
            self.assertTrue(summary["current_score_meets_threshold"])
            self.assertFalse(summary["previous_score_meets_threshold"])
            self.assertFalse((loop_root / "final_readiness.yaml").exists())

    def test_success_requires_two_consecutive_passing_scores(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 90, "READY_FOR_STAGE2", True, [])
            self.write_score(loop_root, 2, 91, "READY_FOR_STAGE2", True, [])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "success")
            self.assertTrue(summary["current_score_meets_threshold"])
            self.assertTrue(summary["previous_score_meets_threshold"])
            final = load_json(loop_root / "final_readiness.yaml")["final_readiness"]
            self.assertEqual(final["status"], "success")

    def test_current_score_over_threshold_continues_when_previous_score_was_low(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 84, "READY_FOR_STAGE2", True, [])
            self.write_score(loop_root, 2, 91, "READY_FOR_STAGE2", True, [])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "continue")
            self.assertTrue(summary["current_score_meets_threshold"])
            self.assertFalse(summary["previous_score_meets_threshold"])

    def test_custom_success_score_threshold_controls_success(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td), success_score_threshold=92)
            self.write_score(loop_root, 1, 91, "READY_FOR_STAGE2", True, [])
            self.write_score(loop_root, 2, 93, "READY_FOR_STAGE2", True, [])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "continue")
            self.assertEqual(summary["success_score_threshold"], 92)
            self.assertTrue(summary["current_score_meets_threshold"])
            self.assertFalse(summary["previous_score_meets_threshold"])

    def test_no_improvement_after_two_rounds(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 60, "NEEDS_REEXTRACTION", False, ["a", "b"])
            self.write_score(loop_root, 2, 60, "NEEDS_REEXTRACTION", False, ["a", "b"])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "no_improvement")

    def test_max_rounds_has_priority_after_current_round_reaches_limit(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td), max_rounds=2)
            self.write_score(loop_root, 1, 60, "NEEDS_REEXTRACTION", False, ["a"])
            self.write_score(loop_root, 2, 70, "READY_WITH_FIXES", False, ["a"])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "max_rounds_reached")

    def test_source_unavailable_blocks_success(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(
                loop_root, 1, 88, "READY_FOR_STAGE2", True, ["source_unavailable"]
            )
            write_json(
                loop_root / "round_001" / "review" / "stage2_readiness.yaml",
                {"source_available": False},
            )

            result = self.run_script(loop_root, 1)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_001" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "source_unavailable")

    def test_repeated_blocker_when_score_improves_but_same_blocker_remains(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 50, "NEEDS_REEXTRACTION", False, ["same_gap"])
            self.write_score(loop_root, 2, 65, "NEEDS_REEXTRACTION", False, ["same_gap"])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "repeated_blocker")

    def test_continue_when_score_improves_and_blockers_change(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            self.write_score(loop_root, 1, 50, "NEEDS_REEXTRACTION", False, ["old_gap"])
            self.write_score(loop_root, 2, 65, "NEEDS_REEXTRACTION", False, ["new_gap"])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "continue")
            self.assertFalse((loop_root / "final_readiness.yaml").exists())

    def test_ready_with_fixes_can_be_accepted_by_manifest(self):
        with TemporaryDirectory() as td:
            loop_root = self.make_loop(Path(td))
            manifest_path = loop_root / "run_manifest.yaml"
            manifest = load_json(manifest_path)
            manifest["acceptable_readiness"].append("READY_WITH_FIXES")
            write_json(manifest_path, manifest)
            self.write_score(loop_root, 1, 86, "READY_WITH_FIXES", True, [])
            self.write_score(loop_root, 2, 87, "READY_WITH_FIXES", True, [])

            result = self.run_script(loop_root, 2)

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = load_json(loop_root / "round_002" / "round_summary.yaml")[
                "round_summary"
            ]
            self.assertEqual(summary["status"], "success")


if __name__ == "__main__":
    unittest.main()
