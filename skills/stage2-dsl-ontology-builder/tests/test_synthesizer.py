import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import parse_stage1, EvidenceGraph
from stage2_synthesizer import synthesize


def test_synthesize_modules():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    outputs = synthesize(graph, output_dir=Path("/tmp/test_stage2_outputs"))
    assert "ontology" in outputs
    assert "modules.yaml" in outputs["ontology"]


def test_module_inference():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    outputs = synthesize(graph, output_dir=Path("/tmp/test_stage2_outputs_2"))

    # tiling.s1_base should map to tiling module
    schema_path = Path("/tmp/test_stage2_outputs_2/schema/modules/tiling.schema.yaml")
    assert schema_path.exists()
    content = schema_path.read_text()
    assert "s1_base" in content


def test_validator_generation():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    outputs = synthesize(graph, output_dir=Path("/tmp/test_stage2_outputs_3"))

    # Should have mandatory validators
    for v_name in ["ub_capacity", "l1_capacity", "workspace_no_alias"]:
        v_path = Path(f"/tmp/test_stage2_outputs_3/validators_spec/{v_name}.yaml")
        assert v_path.exists(), f"Missing validator {v_name}"

    # Should have risk-derived validator
    risk_v_path = Path("/tmp/test_stage2_outputs_3/validators_spec/valid_r_test_1.yaml")
    assert risk_v_path.exists()


def test_synthesizer_writes_agent_ready_artifacts():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_outputs_v04")
    synthesize(graph, output_dir=output_dir)

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

    schedule_space = yaml.safe_load((output_dir / "search" / "schedule_space.yaml").read_text())
    assert schedule_space["version"] == "0.4"
    assert any(item["field"] == "tiling.s1_base" for item in schedule_space["schedule_points"])

    hardware_contract = yaml.safe_load((output_dir / "ir" / "hardware_contract.yaml").read_text())
    assert any(item["name"] == "ub_capacity" for item in hardware_contract["capabilities"])


def test_synthesizer_adds_agent_metadata_to_schema_fields():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = Path("/tmp/test_stage2_outputs_v04_schema")
    synthesize(graph, output_dir=output_dir)

    schema = yaml.safe_load((output_dir / "schema" / "modules" / "tiling.schema.yaml").read_text())
    field = schema["tiling"]["s1_base"]
    assert field["ir_layer"] == "kernel"
    assert "schedule:tiling.s1_base" in field["schedule_points"]
    assert field["feature_sources"]
    assert field["measurement_metrics"]
    assert "schedule_trace" in field["replay_requirements"]
    assert "range" in field or "candidates" in field


def test_synthesizer_bounds_searchable_domains(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)

    schema = yaml.safe_load(
        (output_dir / "schema" / "modules" / "tiling.schema.yaml").read_text()
    )
    field = schema["tiling"]["s1_base"]
    assert "candidates" in field or (
        "range" in field
        and "minimum" in field["range"]
        and "maximum" in field["range"]
    )

    schedule_space = yaml.safe_load((output_dir / "search" / "schedule_space.yaml").read_text())
    schedule_point = next(
        item for item in schedule_space["schedule_points"] if item["field"] == "tiling.s1_base"
    )
    assert "candidates" in schedule_point or (
        "range" in schedule_point
        and "minimum" in schedule_point["range"]
        and "maximum" in schedule_point["range"]
    )


def test_synthesizer_preserves_yaml_contract_types(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    output_dir = tmp_path / "stage2_outputs"
    synthesize(graph, output_dir=output_dir)

    pipeline_schema = yaml.safe_load(
        (output_dir / "schema" / "modules" / "pipeline.schema.yaml").read_text()
    )
    pipeline_kind = pipeline_schema["pipeline"]["kind"]
    assert isinstance(pipeline_kind["schedule_points"], list)
    assert "schedule:pipeline.kind" in pipeline_kind["schedule_points"]

    schedule_space = yaml.safe_load((output_dir / "search" / "schedule_space.yaml").read_text())
    pipeline_schedule = next(
        item for item in schedule_space["schedule_points"] if item["field"] == "pipeline.kind"
    )
    assert pipeline_schedule["source_knob"] is None

    target_schema = yaml.safe_load(
        (output_dir / "schema" / "modules" / "target.schema.yaml").read_text()
    )
    target_ub_capacity = target_schema["target"]["ub_capacity_bytes"]
    assert target_ub_capacity["schedule_points"] == []
