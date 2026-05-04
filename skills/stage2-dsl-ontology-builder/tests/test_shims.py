import json
import subprocess
import sys
from pathlib import Path


def test_bootstrap_shim_generates_v04_outputs(tmp_path):
    skill_dir = Path(__file__).parent.parent
    fixtures = skill_dir / "tests" / "fixtures"
    output_dir = tmp_path / "stage2_outputs"

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
    expected_files = [
        output_dir / "ir" / "semantic_ir.yaml",
        output_dir / "ir" / "kernel_ir.yaml",
        output_dir / "ir" / "hardware_contract.yaml",
        output_dir / "ir" / "execution_feedback.yaml",
        output_dir / "search" / "schedule_space.yaml",
        output_dir / "search" / "feature_schema.yaml",
        output_dir / "search" / "measurement_schema.yaml",
        output_dir / "search" / "tuning_record.schema.yaml",
    ]
    for path in expected_files:
        assert path.exists(), f"missing {path}"


def test_quality_shim_preserves_quality_gate_json(tmp_path):
    skill_dir = Path(__file__).parent.parent
    fixtures = skill_dir / "tests" / "fixtures"
    output_dir = tmp_path / "stage2_outputs"

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
    assert (output_dir / "review" / "agent_readiness.md").exists()
