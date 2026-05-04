import json
import subprocess
import sys
from pathlib import Path


def test_bootstrap_shim_generates_v04_outputs():
    skill_dir = Path(__file__).parent.parent
    fixtures = skill_dir / "tests" / "fixtures"
    output_dir = Path("/tmp/test_stage2_bootstrap_shim_v04")

    result = subprocess.run(
        [
            sys.executable,
            str(skill_dir / "scripts" / "bootstrap_stage2.py"),
            "--input",
            str(fixtures),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / ".evidence_graph.json").exists()
    assert (output_dir / "ir" / "semantic_ir.yaml").exists()
    assert (output_dir / "search" / "schedule_space.yaml").exists()


def test_quality_shim_preserves_quality_gate_json():
    skill_dir = Path(__file__).parent.parent
    fixtures = skill_dir / "tests" / "fixtures"
    output_dir = Path("/tmp/test_stage2_quality_shim_v04")

    subprocess.run(
        [
            sys.executable,
            str(skill_dir / "scripts" / "bootstrap_stage2.py"),
            "--input",
            str(fixtures),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            str(skill_dir / "scripts" / "check_stage2_quality.py"),
            "--input",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    quality_path = output_dir / "review" / "quality_gate.json"
    assert quality_path.exists()
    quality = json.loads(quality_path.read_text())
    assert "overall_status" in quality
    assert "agent_readiness" in quality
