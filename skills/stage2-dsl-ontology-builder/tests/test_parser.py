import sys
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
