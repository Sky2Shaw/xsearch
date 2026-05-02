import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "init_loop.py"


class InitLoopTests(unittest.TestCase):
    def test_initializes_default_loop_root_and_round_one(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source"
            source.mkdir()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--source-root",
                    str(source),
                    "--max-rounds",
                    "4",
                ],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            stdout = json.loads(result.stdout)
            loop_root = source / ".xperf_atdsl_loop"
            self.assertEqual(stdout["loop_root"], str(loop_root))

            extraction_dir = loop_root / "round_001" / "extraction"
            review_dir = loop_root / "round_001" / "review"
            self.assertTrue(extraction_dir.is_dir())
            self.assertTrue(review_dir.is_dir())

            manifest_path = loop_root / "run_manifest.yaml"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_root"], str(source.resolve()))
            self.assertEqual(manifest["max_rounds"], 4)
            self.assertEqual(manifest["rounds"][0]["round"], 1)
            self.assertEqual(manifest["rounds"][0]["status"], "initialized")

    def test_rejects_missing_source_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--source-root", str(missing)],
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("source root must exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
