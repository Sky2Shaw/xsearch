import sys
from textwrap import dedent
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage2_parser import parse_stage1, EvidenceGraph


def test_parse_cards():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)
    assert graph is not None
    assert len(graph.nodes) > 0


def test_card_evidence_connectivity():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)

    card_node = graph.get_node("OC-TEST-CARD-1")
    assert card_node is not None

    # Card should have edge to evidence SE-TEST-1
    ev_edges = [e for e in graph.edges if e.from_id == "OC-TEST-CARD-1" and e.to_id == "SE-TEST-1"]
    assert len(ev_edges) == 1
    assert ev_edges[0].label == "backed_by"


def test_field_knob_link():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)

    field_id = "field:tiling.s1_base"
    knob_id = "knob:s1_base"
    tuned_edges = [e for e in graph.edges if e.from_id == field_id and e.to_id == knob_id]
    assert len(tuned_edges) == 1
    assert tuned_edges[0].label == "tuned_by"


def test_graph_save_load():
    import tempfile
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = Path(f.name)

    graph.save(path)
    loaded = EvidenceGraph.load(path)
    assert len(loaded.nodes) == len(graph.nodes)
    assert len(loaded.edges) == len(graph.edges)
    path.unlink()


def test_agent_ready_graph_nodes_and_edges():
    fixtures = Path(__file__).parent / "fixtures"
    graph = parse_stage1(fixtures)

    kinds = {node.kind for node in graph.nodes}
    assert "semantic_entity" in kinds
    assert "schedule_point" in kinds
    assert "hardware_capability" in kinds
    assert "measurement_metric" in kinds
    assert "feature_source" in kinds
    assert "tuning_record_field" in kinds

    assert graph.get_node("ir:semantic:shape_layout.input_layout") is not None
    assert graph.get_node("ir:kernel:tiling.s1_base") is not None
    assert graph.get_node("ir:hardware:target.ub_capacity_bytes") is not None
    assert graph.get_node("schedule:tiling.s1_base") is not None
    assert graph.get_node("metric:latency_us") is not None
    assert graph.get_node("tuning_record:schedule_trace") is not None

    assert any(
        edge.label == "field_maps_to_ir"
        and edge.from_id == "field:tiling.s1_base"
        and edge.to_id == "ir:kernel:tiling.s1_base"
        for edge in graph.edges
    )
    assert any(
        edge.label == "field_maps_to_ir"
        and edge.from_id == "field:tiling.s1_base"
        and edge.to_id == "schedule:tiling.s1_base"
        for edge in graph.edges
    )
    assert any(
        edge.label == "schedule_point_guarded_by"
        and edge.from_id == "schedule:tiling.s1_base"
        and edge.to_id == "C-TEST-1"
        for edge in graph.edges
    )
    assert any(
        edge.label == "field_requires_capability"
        and edge.from_id == "field:target.ub_capacity_bytes"
        and edge.to_id == "capability:ub_capacity"
        for edge in graph.edges
    )


def test_l1_residency_field_prefers_kernel_namespace_over_capacity_meaning(tmp_path):
    (tmp_path / "optimization_cards.yaml").write_text(dedent("""
        optimization_cards:
          - id: OC-L1-RESIDENCY
            possible_dsl_fields:
              - path: l1_residency.max_tokens
                meaning: Max tokens constrained by L1 capacity
                confidence: high
        """), encoding="utf-8")

    graph = parse_stage1(tmp_path)

    assert graph.get_node("ir:kernel:l1_residency.max_tokens") is not None
    assert graph.get_node("ir:hardware:l1_residency.max_tokens") is None
    assert any(
        edge.label == "field_requires_capability"
        and edge.from_id == "field:l1_residency.max_tokens"
        and edge.to_id == "capability:l1_capacity"
        for edge in graph.edges
    )


def test_shared_capability_node_records_all_source_fields(tmp_path):
    (tmp_path / "optimization_cards.yaml").write_text(dedent("""
        optimization_cards:
          - id: OC-L1-SHARED
            possible_dsl_fields:
              - path: l1_partition.bytes_per_buffer
                meaning: L1 partition capacity per buffer
                confidence: high
              - path: l1_residency.max_tokens
                meaning: Max tokens resident in L1
                confidence: high
        """), encoding="utf-8")

    graph = parse_stage1(tmp_path)

    capability_node = graph.get_node("capability:l1_capacity")
    assert capability_node is not None
    assert capability_node.data["source_fields"] == [
        "l1_partition.bytes_per_buffer",
        "l1_residency.max_tokens",
    ]
