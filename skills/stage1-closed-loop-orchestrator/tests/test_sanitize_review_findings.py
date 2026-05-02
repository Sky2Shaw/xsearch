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
            (review / "score_report.md").write_text(
                "Long scorer narrative that must not appear.\n", encoding="utf-8"
            )

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
            self.assertEqual(
                request["required_fixes"][0]["id"], "missing_flash_decode_merge"
            )
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

    def test_preserves_structured_required_evidence(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            review = root / "review"
            output = root / "reextraction_request.yaml"
            write_json(
                review / "blocking_findings.yaml",
                {
                    "blocking_findings": [
                        {
                            "id": "needs_line_ranges",
                            "severity": "major",
                            "dimension": "traceability",
                            "required_evidence": ["file", "line_range"],
                            "source_or_artifact_ref": [{"path": "op/kernel.cpp"}],
                        }
                    ]
                },
            )

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
            request = load_json(output)["reextraction_request"]
            self.assertEqual(
                request["required_fixes"][0]["required_evidence"],
                ["file", "line_range"],
            )

    def test_generates_score_improvement_targets_from_scorecard_dimensions(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            review = root / "review"
            output = root / "reextraction_request.yaml"
            write_json(
                review / "scorecard.yaml",
                {
                    "scorecard": {
                        "total": 71,
                        "readiness": "NEEDS_REEXTRACTION",
                        "dimensions": {
                            "coverage": {"score": 13, "max": 25},
                            "accuracy": {"score": 22, "max": 25},
                            "traceability": {"score": 8, "max": 15},
                        },
                    }
                },
            )
            write_json(
                review / "blocking_findings.yaml",
                {
                    "blocking_findings": [
                        {
                            "id": "missing_l1_residency",
                            "severity": "blocking",
                            "dimension": "coverage",
                            "target_symbols": ["LoadKVToL1"],
                            "required_artifacts": ["cards/l1_residency.yaml"],
                        },
                        {
                            "id": "weak_source_links",
                            "severity": "major",
                            "dimension": "traceability",
                            "target_files": ["op/kernel.cpp"],
                            "required_evidence": ["file", "function", "line_range"],
                        },
                    ]
                },
            )

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
            request = load_json(output)["reextraction_request"]
            self.assertEqual(
                request["required_fixes"][0]["id"], "missing_l1_residency"
            )
            self.assertIn(
                "operator_info_needed", request["required_fixes"][0]
            )
            targets = request["score_improvement_targets"]
            self.assertEqual(targets[0]["dimension"], "coverage")
            self.assertEqual(targets[0]["current_score"], 13)
            self.assertEqual(targets[0]["max_score"], 25)
            self.assertEqual(targets[0]["score_gap"], 12)
            self.assertEqual(
                targets[0]["related_finding_ids"], ["missing_l1_residency"]
            )
            self.assertIn("LoadKVToL1", targets[0]["target_symbols"])
            self.assertIn("cards/l1_residency.yaml", targets[0]["required_artifacts"])


if __name__ == "__main__":
    unittest.main()
