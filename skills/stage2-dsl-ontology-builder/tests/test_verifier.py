import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import parse_stage1, EvidenceGraph
from stage2_synthesizer import synthesize
from stage2_verifier import verify


def test_verifier_runs():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify")
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)
    assert "overall_status" in result


def test_verifier_score_range():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_2")
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)
    assert 0 <= result["total_score"] <= 100
    assert result["overall_status"] in ("pass", "warn", "fail")
    assert "semantic_issues" in result


def test_verifier_mandatory_validators():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_3")
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)

    # With minimal fixtures, some mandatory validators won't have evidence
    # so score should be < 85 but >= 0
    assert result["total_score"] < 85  # because mandatory validators have placeholders
    assert result["overall_status"] == "warn" or result["overall_status"] == "fail"
