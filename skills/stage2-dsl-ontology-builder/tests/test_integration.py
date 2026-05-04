import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import parse_stage1
from stage2_synthesizer import synthesize
from stage2_verifier import verify


def test_full_pipeline_on_real_data(tmp_path):
    """Run full pipeline against actual Stage 1 extraction."""
    input_dir = Path("artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction")
    if not input_dir.exists():
        import pytest
        pytest.skip("Real Stage 1 data not available")

    output_dir = tmp_path / "stage2_outputs"
    graph = parse_stage1(input_dir)
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    synthesize(graph, output_dir=output_dir)
    assert (output_dir / "ontology" / "canonical_optimizations.yaml").exists()
    assert (output_dir / "schema" / "atdsl.schema.yaml").exists()
    assert (output_dir / "ir" / "semantic_ir.yaml").exists()
    assert (output_dir / "ir" / "kernel_ir.yaml").exists()
    assert (output_dir / "ir" / "hardware_contract.yaml").exists()
    assert (output_dir / "ir" / "execution_feedback.yaml").exists()
    assert (output_dir / "search" / "schedule_space.yaml").exists()
    assert (output_dir / "search" / "feature_schema.yaml").exists()
    assert (output_dir / "search" / "measurement_schema.yaml").exists()
    assert (output_dir / "search" / "tuning_record.schema.yaml").exists()

    result = verify(graph, output_dir)
    assert "agent_readiness" in result
    assert (output_dir / "review" / "agent_readiness.md").exists()
    assert result["total_score"] >= 0
    assert result["overall_status"] in ("pass", "warn", "fail")

    # Verify evidence graph is non-trivial
    card_count = len([n for n in graph.nodes if n.kind == "card"])
    assert card_count > 0
    print(f"Parsed {card_count} cards, {len(graph.nodes)} total nodes")
