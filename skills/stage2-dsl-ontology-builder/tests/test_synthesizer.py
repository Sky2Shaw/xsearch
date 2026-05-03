import sys
from pathlib import Path

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
