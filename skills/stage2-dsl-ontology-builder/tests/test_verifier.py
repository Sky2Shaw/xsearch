import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import EvidenceEdge, EvidenceGraph, EvidenceNode, parse_stage1
from stage2_synthesizer import synthesize
from stage2_verifier import _check_field_completeness, _check_knob_quality, verify


def test_verifier_runs(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)
    assert "overall_status" in result


def test_verifier_score_range(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)
    assert 0 <= result["total_score"] <= 100
    assert result["overall_status"] in ("pass", "warn", "fail")
    assert "semantic_issues" in result


def test_verifier_mandatory_validators(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)

    # With minimal fixtures, some mandatory validators won't have evidence
    # so score should be < 85 but >= 0
    assert result["total_score"] < 85  # because mandatory validators have placeholders
    if result["hard_failures"]:
        assert result["overall_status"] == "fail"
    else:
        assert result["overall_status"] == "warn"


def test_field_completeness_accepts_finite_domains_and_rejects_open_ranges(tmp_path):
    stage2_dir = tmp_path / "stage2"
    schema_dir = stage2_dir / "schema" / "modules"
    schema_dir.mkdir(parents=True)
    (schema_dir / "sample.schema.yaml").write_text(
        yaml.safe_dump(
            {
                "sample": {
                    "finite_candidates": {
                        "type": "int",
                        "searchable": True,
                        "candidates": [1, 2, 3],
                    },
                    "finite_enum": {
                        "type": "enum",
                        "searchable": True,
                        "enum": ["a", "b"],
                    },
                    "finite_range": {
                        "type": "int",
                        "searchable": True,
                        "range": {"minimum": 1, "maximum": 8},
                    },
                    "open_range": {
                        "type": "int",
                        "searchable": True,
                        "range": {"minimum": 1},
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    score, issues = _check_field_completeness(stage2_dir, EvidenceGraph())

    assert score <= 20
    assert any("open_range" in issue["message"] for issue in issues)
    assert not any("finite_candidates" in issue["message"] for issue in issues)
    assert not any("finite_enum" in issue["message"] for issue in issues)
    assert not any("finite_range" in issue["message"] for issue in issues)


def test_knob_quality_requires_mapping_and_finite_domain(tmp_path):
    stage2_dir = tmp_path / "stage2"
    schema_dir = stage2_dir / "schema" / "modules"
    schema_dir.mkdir(parents=True)
    (schema_dir / "sample.schema.yaml").write_text(
        yaml.safe_dump(
            {
                "sample": {
                    "mapped": {"type": "int", "searchable": True, "candidates": [1, 2, 3]},
                    "unmapped": {"type": "int", "searchable": True, "candidates": [1, 2, 3]},
                    "open_domain": {
                        "type": "int",
                        "searchable": True,
                        "range": {"minimum": 1},
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    graph = EvidenceGraph(
        nodes=[
            EvidenceNode(id="field:sample.mapped", kind="dsl_field", data={"path": "sample.mapped"}),
            EvidenceNode(id="field:sample.unmapped", kind="dsl_field", data={"path": "sample.unmapped"}),
            EvidenceNode(id="field:sample.open_domain", kind="dsl_field", data={"path": "sample.open_domain"}),
            EvidenceNode(
                id="knob:sample_mapped",
                kind="knob",
                data={"name": "sample_mapped", "domain": {"candidates": [1, 2, 3]}},
            ),
            EvidenceNode(
                id="knob:sample_open_domain",
                kind="knob",
                data={"name": "sample_open_domain", "domain": {"kind": "positive_integer", "minimum": 1}},
            ),
        ],
        edges=[
            EvidenceEdge(from_id="field:sample.mapped", to_id="knob:sample_mapped", label="tuned_by"),
            EvidenceEdge(from_id="field:sample.open_domain", to_id="knob:sample_open_domain", label="tuned_by"),
        ],
    )

    score, issues = _check_knob_quality(graph, stage2_dir)

    assert score <= 15
    assert any("sample.unmapped" in issue["message"] for issue in issues)
    assert any("sample_open_domain" in issue["message"] for issue in issues)


def test_verifier_reports_agent_readiness(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)
    result = verify(graph, output_dir)

    assert "agent_readiness" in result
    readiness = result["agent_readiness"]
    assert readiness["status"] in ("pass", "warn", "fail")
    assert 0 <= readiness["score"] <= 100
    assert "schedule_space_quality" in readiness["scores"]
    assert (output_dir / "review" / "agent_readiness.md").exists()


def test_verifier_fails_schedule_point_without_guard(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)

    schedule_path = output_dir / "search" / "schedule_space.yaml"
    data = yaml.safe_load(schedule_path.read_text())
    data["schedule_points"][0]["guard_validators"] = []
    schedule_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    result = verify(graph, output_dir)
    assert "Schedule point has no validator guard" in " ".join(result["agent_readiness"]["hard_failures"])
    assert "Schedule point has no validator guard" in " ".join(result["hard_failures"])
    assert result["overall_status"] == "fail"


def test_verifier_fails_when_legacy_hard_failures_exist(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)
    (output_dir / "validators_spec" / "ub_capacity.yaml").unlink()

    result = verify(graph, output_dir)

    assert "Missing mandatory validator: ub_capacity" in result["hard_failures"]
    assert result["overall_status"] == "fail"


def test_verifier_accepts_bounded_searchable_domains(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)

    result = verify(graph, output_dir)

    messages = [issue["message"] for issue in result["semantic_issues"]]
    assert not any("Searchable field tiling.s1_base has no candidates/range/enum" in msg for msg in messages)
    readiness_messages = [issue["message"] for issue in result["agent_readiness"]["issues"]]
    assert not any("Searchable field tiling.s1_base has no range, candidates, or enum" in msg for msg in readiness_messages)


def test_verifier_rejects_open_ended_searchable_schema_domain(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)

    schema_path = output_dir / "schema" / "modules" / "tiling.schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["tiling"]["s1_base"].pop("candidates", None)
    schema["tiling"]["s1_base"]["range"] = {"minimum": 1, "unit": "tokens"}
    schema_path.write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")

    result = verify(graph, output_dir)

    messages = [issue["message"] for issue in result["semantic_issues"]]
    assert "Searchable field tiling.s1_base has no finite candidates/range/enum" in messages


def test_verifier_rejects_schema_domain_that_does_not_map_to_source_knob(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)

    schema_path = output_dir / "schema" / "modules" / "tiling.schema.yaml"
    schema = yaml.safe_load(schema_path.read_text())
    schema["tiling"]["s1_base"]["candidates"] = [999]
    schema_path.write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")

    result = verify(graph, output_dir)

    messages = [issue["message"] for issue in result["semantic_issues"]]
    assert "Knob s1_base domain is not mapped to searchable field tiling.s1_base" in messages


def test_verifier_rejects_unlinked_hardware_contract(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)

    hardware_path = output_dir / "ir" / "hardware_contract.yaml"
    hardware = yaml.safe_load(hardware_path.read_text())
    hardware["capabilities"] = [{
        "id": "capability:unrelated",
        "name": "unrelated",
        "source_fields": ["target.unrelated"],
    }]
    hardware_path.write_text(yaml.safe_dump(hardware, sort_keys=False), encoding="utf-8")

    result = verify(graph, output_dir)

    assert "Hardware field target.ub_capacity_bytes has no linked hardware contract" in result["hard_failures"]
    assert result["overall_status"] == "fail"
