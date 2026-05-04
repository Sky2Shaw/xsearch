import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import yaml

from stage2_parser import EvidenceEdge, EvidenceGraph, EvidenceNode, parse_stage1
from stage2_synthesizer import synthesize
from stage2_verifier import _check_field_completeness, _check_knob_quality, verify


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
    assert result["hard_failures"]
    assert result["overall_status"] == "fail"


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
