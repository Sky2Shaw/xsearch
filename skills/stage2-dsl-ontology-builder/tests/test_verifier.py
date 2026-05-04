import sys
from pathlib import Path

import yaml

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
    if result["hard_failures"]:
        assert result["overall_status"] == "fail"
    else:
        assert result["overall_status"] == "warn"


def test_verifier_reports_agent_readiness():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_v04")
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)

    assert "agent_readiness" in result
    readiness = result["agent_readiness"]
    assert readiness["status"] in ("pass", "warn", "fail")
    assert 0 <= readiness["score"] <= 100
    assert "schedule_space_quality" in readiness["scores"]
    assert (output_dir / "review" / "agent_readiness.md").exists()


def test_verifier_fails_schedule_point_without_guard():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_v04_bad_schedule")
    synthesize(graph, output_dir=output_dir)

    schedule_path = output_dir / "search" / "schedule_space.yaml"
    data = yaml.safe_load(schedule_path.read_text())
    data["schedule_points"][0]["guard_validators"] = []
    schedule_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = verify(graph, output_dir)
    assert "Schedule point has no validator guard" in " ".join(result["agent_readiness"]["hard_failures"])
    assert result["overall_status"] == "fail"


def test_verifier_fails_when_legacy_hard_failures_exist():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_v04_legacy_hard_failure")
    synthesize(graph, output_dir=output_dir)
    (output_dir / "validators_spec" / "ub_capacity.yaml").unlink()

    result = verify(graph, output_dir)

    assert "Missing mandatory validator: ub_capacity" in result["hard_failures"]
    assert result["overall_status"] == "fail"


def test_verifier_accepts_bounded_searchable_domains():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_v04_finite_domains")
    synthesize(graph, output_dir=output_dir)

    result = verify(graph, output_dir)

    messages = [issue["message"] for issue in result["semantic_issues"]]
    assert not any("Searchable field tiling.s1_base has no candidates/range/enum" in msg for msg in messages)
    readiness_messages = [issue["message"] for issue in result["agent_readiness"]["issues"]]
    assert not any("Searchable field tiling.s1_base has no range, candidates, or enum" in msg for msg in readiness_messages)


def test_verifier_rejects_open_ended_searchable_schema_domain():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_verify_v04_open_domain")
    synthesize(graph, output_dir=output_dir)

    schema_path = output_dir / "schema" / "modules" / "tiling.schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["tiling"]["s1_base"].pop("candidates", None)
    schema["tiling"]["s1_base"]["range"] = {"minimum": 1, "unit": "tokens"}
    schema_path.write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")

    result = verify(graph, output_dir)

    messages = [issue["message"] for issue in result["semantic_issues"]]
    assert "Searchable field tiling.s1_base has no finite candidates/range/enum" in messages
