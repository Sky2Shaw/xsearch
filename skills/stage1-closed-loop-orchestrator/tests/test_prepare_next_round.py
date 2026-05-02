import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_next_round.py"


def write_json(path, data):
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def make_loop(root, copy_mode="copy"):
    root = Path(root)
    source_root = root / "operator"
    loop_root = root / ".xperf_atdsl_loop"
    round_dir = loop_root / "round_001"
    extraction_dir = round_dir / "extraction"
    review_dir = round_dir / "review"

    source_root.mkdir(parents=True)
    (extraction_dir / "reports").mkdir(parents=True)
    review_dir.mkdir(parents=True)
    write_json(extraction_dir / "reports" / "function_index.yaml", {"functions": []})

    manifest = {
        "run_id": "run-1",
        "source_root": str(source_root),
        "loop_root": str(loop_root.resolve()),
        "max_rounds": 3,
        "acceptable_readiness": ["READY_FOR_STAGE2"],
        "copy_mode": copy_mode,
        "rounds": [
            {
                "round": 1,
                "round_dir": str(round_dir),
                "extraction_dir": str(extraction_dir),
                "review_dir": str(review_dir),
                "status": "complete",
            }
        ],
    }
    write_json(loop_root / "run_manifest.yaml", manifest)
    return loop_root


def run_prepare(loop_root):
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--loop-root",
            str(loop_root),
            "--from-round",
            "1",
            "--to-round",
            "2",
        ],
        text=True,
        capture_output=True,
    )


class PrepareNextRoundTests(unittest.TestCase):
    def test_copy_mode_copies_previous_artifacts_and_updates_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir), copy_mode="copy")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--loop-root",
                    str(loop_root),
                    "--from-round",
                    "1",
                    "--to-round",
                    "2",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            target_artifact = (
                loop_root / "round_002" / "extraction" / "reports" / "function_index.yaml"
            )
            self.assertTrue(target_artifact.is_file())
            self.assertTrue((loop_root / "round_002" / "review").is_dir())

            context = load_json(loop_root / "round_002" / "next_round_context.yaml")
            self.assertEqual(context["from_round"], 1)
            self.assertEqual(context["to_round"], 2)
            self.assertEqual(context["source_root"], str(Path(tmpdir) / "operator"))
            self.assertEqual(
                context["previous_artifact_root"],
                str(loop_root / "round_001" / "extraction"),
            )
            self.assertEqual(
                context["output_artifact_root"],
                str(loop_root / "round_002" / "extraction"),
            )
            self.assertEqual(context["copy_mode"], "copy")
            self.assertEqual(output, context)

            manifest = load_json(loop_root / "run_manifest.yaml")
            self.assertEqual(manifest["rounds"][1]["round"], 2)
            self.assertEqual(manifest["rounds"][1]["status"], "initialized")

    def test_reference_mode_does_not_copy_but_creates_output_dirs_and_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir), copy_mode="reference")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--loop-root",
                    str(loop_root),
                    "--from-round",
                    "1",
                    "--to-round",
                    "2",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            copied_artifact = (
                loop_root / "round_002" / "extraction" / "reports" / "function_index.yaml"
            )
            self.assertTrue((loop_root / "round_002" / "extraction").is_dir())
            self.assertFalse(copied_artifact.exists())
            self.assertTrue((loop_root / "round_002" / "review").is_dir())

            context = load_json(loop_root / "round_002" / "next_round_context.yaml")
            self.assertEqual(context["copy_mode"], "reference")
            self.assertEqual(
                context["previous_artifact_root"],
                str(loop_root / "round_001" / "extraction"),
            )

    def test_existing_to_round_manifest_metadata_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir), copy_mode="reference")
            manifest_path = loop_root / "run_manifest.yaml"
            manifest = load_json(manifest_path)
            manifest["rounds"].append(
                {
                    "round": 2,
                    "round_dir": "stale-round-dir",
                    "extraction_dir": "stale-extraction-dir",
                    "review_dir": "stale-review-dir",
                    "status": "stale",
                    "manual_note": "keep-me",
                }
            )
            write_json(manifest_path, manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--loop-root",
                    str(loop_root),
                    "--from-round",
                    "1",
                    "--to-round",
                    "2",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = load_json(manifest_path)
            round_two = next(
                round_record
                for round_record in manifest["rounds"]
                if round_record["round"] == 2
            )
            self.assertEqual(round_two["manual_note"], "keep-me")
            self.assertEqual(round_two["round_dir"], str(loop_root / "round_002"))
            self.assertEqual(
                round_two["extraction_dir"],
                str(loop_root / "round_002" / "extraction"),
            )
            self.assertEqual(round_two["review_dir"], str(loop_root / "round_002" / "review"))
            self.assertEqual(round_two["status"], "initialized")

    def test_rejects_missing_previous_round(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir))
            manifest_path = loop_root / "run_manifest.yaml"
            manifest = load_json(manifest_path)
            manifest["rounds"] = []
            write_json(manifest_path, manifest)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--loop-root",
                    str(loop_root),
                    "--from-round",
                    "1",
                    "--to-round",
                    "2",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("from round not found", result.stderr)

    def test_rejects_non_increasing_round(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir))

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--loop-root",
                    str(loop_root),
                    "--from-round",
                    "2",
                    "--to-round",
                    "2",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("to-round must be greater", result.stderr)

    def test_invalid_copy_mode_returns_2_without_creating_next_round(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir), copy_mode="mirror")

            result = run_prepare(loop_root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("copy_mode", result.stderr)
            self.assertFalse((loop_root / "round_002").exists())

    def test_missing_source_root_returns_2_without_creating_next_round(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir))
            manifest_path = loop_root / "run_manifest.yaml"
            manifest = load_json(manifest_path)
            del manifest["source_root"]
            write_json(manifest_path, manifest)

            result = run_prepare(loop_root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("source_root", result.stderr)
            self.assertFalse((loop_root / "round_002").exists())

    def test_malformed_rounds_returns_2_without_creating_next_round(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir))
            manifest_path = loop_root / "run_manifest.yaml"
            manifest = load_json(manifest_path)
            manifest["rounds"] = {"round": 1}
            write_json(manifest_path, manifest)

            result = run_prepare(loop_root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("rounds", result.stderr)
            self.assertFalse((loop_root / "round_002").exists())

    def test_previous_round_missing_extraction_dir_returns_2_without_creating_next_round(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            loop_root = make_loop(Path(tmpdir))
            manifest_path = loop_root / "run_manifest.yaml"
            manifest = load_json(manifest_path)
            del manifest["rounds"][0]["extraction_dir"]
            write_json(manifest_path, manifest)

            result = run_prepare(loop_root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("extraction_dir", result.stderr)
            self.assertFalse((loop_root / "round_002").exists())

    def test_rejects_copy_path_overlaps_without_removing_previous_artifacts(self):
        cases = {
            "same path": lambda loop_root: loop_root / "round_002" / "extraction",
            "target inside previous": lambda loop_root: loop_root,
            "previous inside target": lambda loop_root: (
                loop_root / "round_002" / "extraction" / "previous"
            ),
        }
        for name, previous_root_factory in cases.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    loop_root = make_loop(Path(tmpdir))
                    previous_root = previous_root_factory(loop_root)
                    previous_root.mkdir(parents=True, exist_ok=True)
                    sentinel = previous_root / "sentinel.txt"
                    sentinel.write_text("keep", encoding="utf-8")

                    manifest_path = loop_root / "run_manifest.yaml"
                    manifest = load_json(manifest_path)
                    manifest["rounds"][0]["extraction_dir"] = str(previous_root)
                    write_json(manifest_path, manifest)

                    result = run_prepare(loop_root)

                    self.assertEqual(result.returncode, 2)
                    self.assertRegex(result.stderr, r"overlaps?")
                    self.assertTrue(sentinel.is_file())


if __name__ == "__main__":
    unittest.main()
