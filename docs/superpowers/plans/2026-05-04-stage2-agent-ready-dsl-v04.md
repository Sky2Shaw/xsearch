# Stage 2 Agent-Ready DSL v0.4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `stage2-dsl-ontology-builder` so Stage 2 emits and verifies agent-ready DSL contracts for semantic IR, kernel IR, hardware contracts, execution feedback, schedule search, features, measurements, and replay records.

**Architecture:** Keep the existing v0.3 parser -> synthesizer -> verifier pipeline. Add v0.4 graph node kinds and edge labels in `stage2_parser.py`, generate new `ir/` and `search/` artifacts plus schema metadata in `stage2_synthesizer.py`, and add an `agent_readiness` verifier section in `stage2_verifier.py`. Preserve every existing output path and shim entrypoint.

**Tech Stack:** Python 3.11, standard library, PyYAML, pytest.

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py` | Parse Stage 1 YAML into EvidenceGraph and add v0.4 IR/search/feedback graph nodes. |
| `skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py` | Generate legacy Stage 2 artifacts plus v0.4 `ir/` and `search/` contracts. |
| `skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py` | Verify legacy semantic quality and v0.4 agent readiness. |
| `skills/stage2-dsl-ontology-builder/tests/fixtures/optimization_cards.yaml` | Fixture fields that exercise semantic, kernel, and hardware layers. |
| `skills/stage2-dsl-ontology-builder/tests/test_parser.py` | Parser unit coverage for v0.4 node kinds and edges. |
| `skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py` | Synthesizer unit coverage for new artifacts and schema metadata. |
| `skills/stage2-dsl-ontology-builder/tests/test_verifier.py` | Verifier unit coverage for `agent_readiness` and hard failures. |
| `skills/stage2-dsl-ontology-builder/tests/test_integration.py` | Real-artifact pipeline coverage for v0.4 outputs. |
| `skills/stage2-dsl-ontology-builder/SKILL.md` | Skill workflow and final-response contract. |
| `skills/stage2-dsl-ontology-builder/README.md` | Quick-start command documentation. |
| `skills/stage2-dsl-ontology-builder/references/*.md` | Output contract, workflow, schema rules, verifier rules, and lowering guidance. |
| `skills/stage2-dsl-ontology-builder/agents/openai.yaml` | Agent role hints for v0.4 work. |

## Task 1: Parser v0.4 Graph Contracts

**Files:**
- Modify: `skills/stage2-dsl-ontology-builder/tests/fixtures/optimization_cards.yaml`
- Modify: `skills/stage2-dsl-ontology-builder/tests/test_parser.py`
- Modify: `skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py`

- [ ] **Step 1: Expand the fixture with semantic and hardware fields**

In `skills/stage2-dsl-ontology-builder/tests/fixtures/optimization_cards.yaml`, replace the `possible_dsl_fields` block with:

```yaml
    possible_dsl_fields:
      - path: shape_layout.input_layout
        meaning: Input tensor layout mode
        confidence: high
      - path: tiling.s1_base
        meaning: Base S1 tile size in tokens
        confidence: high
      - path: pipeline.kind
        meaning: Pipeline variant kind
        confidence: medium
      - path: target.ub_capacity_bytes
        meaning: Target UB capacity size in bytes
        confidence: high
```

- [ ] **Step 2: Write failing parser tests**

Append this to `skills/stage2-dsl-ontology-builder/tests/test_parser.py`:

```python
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
```

- [ ] **Step 3: Run parser tests and verify the new test fails**

Run:

```bash
python -m pytest skills/stage2-dsl-ontology-builder/tests/test_parser.py -v
```

Expected: the new test fails because the parser has not created v0.4 node kinds.

- [ ] **Step 4: Add parser constants and helpers**

In `skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py`, add these constants after `_resolve_file`:

```python
SEMANTIC_TOKENS = {"interface", "shape", "shape_layout", "layout", "compute", "features"}
KERNEL_TOKENS = {
    "tiling", "core_mapping", "memory", "l1_partition", "l1_residency",
    "workspace", "pipeline", "decode", "flash_decode", "sparse_window",
    "tail_policy",
}
HARDWARE_TOKENS = {"target"}
EXECUTION_TOKENS = {"search", "lowering"}

SCHEDULE_TOKENS = {
    "tiling", "core_mapping", "memory", "l1_partition", "l1_residency",
    "pipeline", "decode", "flash_decode", "sparse_window", "tail_policy",
}

CAPABILITY_BY_TOKEN = {
    "target": ["target_capability"],
    "memory": ["memory_space"],
    "l1_partition": ["l1_capacity"],
    "l1_residency": ["l1_capacity"],
    "workspace": ["workspace_capacity", "workspace_aliasing"],
    "sparse_window": ["alignment"],
}

DEFAULT_METRICS = [
    "latency_us",
    "throughput_ops",
    "bytes_global",
    "bytes_shared",
    "occupancy_estimate",
    "compile_time_ms",
    "correctness",
    "failure_code",
]

FEATURE_SOURCES = [
    "structural.loop_extents",
    "structural.reduction_depth",
    "memory.working_set",
    "memory.scope_reuse",
    "mapping.core_thread_mapping",
    "mapping.intrinsic_match",
    "history.similar_shape_key",
    "history.failure_category",
]

TUNING_RECORD_FIELDS = [
    "environment_fingerprint",
    "shape_signature",
    "dsl_version",
    "schedule_trace",
    "validator_results",
    "compile_result",
    "measurement_result",
    "failure_metadata",
]
```

Then add these helper functions below the constants:

```python
def _add_node_once(graph: EvidenceGraph, node_id: str, kind: str, data: dict[str, Any]) -> None:
    if graph.get_node(node_id) is None:
        graph.add_node(EvidenceNode(id=node_id, kind=kind, data=data))


def _add_edge_once(graph: EvidenceGraph, from_id: str, to_id: str, label: str) -> None:
    if not any(e.from_id == from_id and e.to_id == to_id and e.label == label for e in graph.edges):
        graph.add_edge(EvidenceEdge(from_id=from_id, to_id=to_id, label=label))


def _first_path_token(field_path: str) -> str:
    return field_path.split(".")[0] if "." in field_path else field_path


def _infer_ir_layer(field_path: str, meaning: str) -> str:
    token = _first_path_token(field_path)
    lowered = meaning.lower()
    if token in SEMANTIC_TOKENS or any(word in lowered for word in ("formula", "identity", "tensor", "dtype", "layout")):
        return "semantic"
    if token in HARDWARE_TOKENS or any(word in lowered for word in ("capacity", "target", "ub", "l1")):
        return "hardware"
    if token in EXECUTION_TOKENS or any(word in lowered for word in ("metric", "trace", "record", "measure")):
        return "execution_feedback"
    if token in KERNEL_TOKENS:
        return "kernel"
    return "needs_review"


def _ir_node_kind(layer: str) -> str:
    if layer == "semantic":
        return "semantic_entity"
    if layer == "kernel":
        return "semantic_entity"
    if layer == "hardware":
        return "hardware_capability"
    if layer == "execution_feedback":
        return "tuning_record_field"
    return "semantic_entity"


def _schedule_point_for_field(field_path: str, has_knob: bool) -> str | None:
    token = _first_path_token(field_path)
    if token in SCHEDULE_TOKENS or has_knob:
        return f"schedule:{field_path}"
    return None


def _capabilities_for_field(field_path: str) -> list[str]:
    token = _first_path_token(field_path)
    capabilities = list(CAPABILITY_BY_TOKEN.get(token, []))
    lowered = field_path.lower()
    if "ub" in lowered and "ub_capacity" not in capabilities:
        capabilities.append("ub_capacity")
    if "l1" in lowered and "l1_capacity" not in capabilities:
        capabilities.append("l1_capacity")
    return sorted(set(capabilities))


def _source_cards_for_field(graph: EvidenceGraph, field_id: str) -> list[str]:
    return sorted({
        edge.from_id
        for edge in graph.edges
        if edge.to_id == field_id and edge.label == "suggests"
    })


def _guard_ids_for_field(graph: EvidenceGraph, field_id: str) -> list[str]:
    guards: set[str] = set()
    for card_id in _source_cards_for_field(graph, field_id):
        for edge in graph.edges:
            if edge.from_id == card_id and edge.label in {"constrained_by", "risked_by"}:
                guards.add(edge.to_id)
    for edge in graph.edges:
        if edge.from_id == field_id and edge.label == "tuned_by":
            knob_node = graph.get_node(edge.to_id)
            if knob_node:
                guards.update(knob_node.data.get("coupled_constraints", []))
    return sorted(guards)
```

- [ ] **Step 5: Add v0.4 nodes after field/knob links**

Add this function below `_link_fields_to_knobs`:

```python
def _add_agent_ready_nodes(graph: EvidenceGraph) -> None:
    field_nodes = [node for node in graph.nodes if node.kind == "dsl_field"]

    for field_node in field_nodes:
        field_path = field_node.data.get("path", "")
        meaning = field_node.data.get("meaning", "")
        has_knob = any(
            edge.from_id == field_node.id and edge.label == "tuned_by"
            for edge in graph.edges
        )
        layer = _infer_ir_layer(field_path, meaning)
        ir_node_id = f"ir:{layer}:{field_path}"
        _add_node_once(graph, ir_node_id, _ir_node_kind(layer), {
            "field_path": field_path,
            "ir_layer": layer,
            "meaning": meaning,
            "confidence": field_node.data.get("confidence", "medium"),
        })
        _add_edge_once(graph, field_node.id, ir_node_id, "field_maps_to_ir")

        schedule_id = _schedule_point_for_field(field_path, has_knob)
        if schedule_id:
            _add_node_once(graph, schedule_id, "schedule_point", {
                "field_path": field_path,
                "action": _first_path_token(field_path),
                "searchable": has_knob,
                "ir_layer": "kernel",
            })
            _add_edge_once(graph, field_node.id, schedule_id, "field_maps_to_ir")
            for guard_id in _guard_ids_for_field(graph, field_node.id):
                _add_edge_once(graph, schedule_id, guard_id, "schedule_point_guarded_by")

        for capability in _capabilities_for_field(field_path):
            capability_id = f"capability:{capability}"
            _add_node_once(graph, capability_id, "hardware_capability", {
                "name": capability,
                "source_field": field_path,
            })
            _add_edge_once(graph, field_node.id, capability_id, "field_requires_capability")

    for metric in DEFAULT_METRICS:
        metric_id = f"metric:{metric}"
        _add_node_once(graph, metric_id, "measurement_metric", {"name": metric})
        for field_node in field_nodes:
            _add_edge_once(graph, metric_id, field_node.id, "metric_measures_field")

    for feature in FEATURE_SOURCES:
        feature_id = f"feature:{feature}"
        _add_node_once(graph, feature_id, "feature_source", {"name": feature})
        for field_node in field_nodes:
            _add_edge_once(graph, feature_id, field_node.id, "feature_derived_from")

    for record_field in TUNING_RECORD_FIELDS:
        _add_node_once(graph, f"tuning_record:{record_field}", "tuning_record_field", {
            "name": record_field,
            "required": True,
        })
```

In `parse_stage1`, after `_link_fields_to_knobs(graph)`, add:

```python
    _add_agent_ready_nodes(graph)
```

- [ ] **Step 6: Run parser tests**

Run:

```bash
python -m pytest skills/stage2-dsl-ontology-builder/tests/test_parser.py -v
```

Expected: all parser tests pass.

- [ ] **Step 7: Commit parser changes**

```bash
git add skills/stage2-dsl-ontology-builder/tests/fixtures/optimization_cards.yaml \
        skills/stage2-dsl-ontology-builder/tests/test_parser.py \
        skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py
git commit -m "feat(stage2): add agent-ready evidence graph nodes"
```

## Task 2: Synthesizer v0.4 IR and Search Artifacts

**Files:**
- Modify: `skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py`
- Modify: `skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py`

- [ ] **Step 1: Write failing synthesizer tests**

Append this to `skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py`:

```python
import yaml


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
    assert "range" in field
```

- [ ] **Step 2: Run synthesizer tests and verify the new tests fail**

Run:

```bash
python -m pytest skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py -v
```

Expected: the new tests fail because `ir/` and `search/` files are not generated.

- [ ] **Step 3: Add graph query helpers to the synthesizer**

In `skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py`, add these helpers above `_build_module_schemas`:

```python
def _edges_from(graph: EvidenceGraph, node_id: str, label: str | None = None) -> list:
    return [
        edge for edge in graph.edges
        if edge.from_id == node_id and (label is None or edge.label == label)
    ]


def _edges_to(graph: EvidenceGraph, node_id: str, label: str | None = None) -> list:
    return [
        edge for edge in graph.edges
        if edge.to_id == node_id and (label is None or edge.label == label)
    ]


def _nodes_by_kind(graph: EvidenceGraph, kind: str) -> list[EvidenceNode]:
    return [node for node in graph.nodes if node.kind == kind]


def _field_path_for_node(node: EvidenceNode) -> str:
    return node.data.get("path") or node.data.get("field_path", "")


def _knob_for_field(graph: EvidenceGraph, field_id: str) -> EvidenceNode | None:
    for edge in _edges_from(graph, field_id, "tuned_by"):
        knob = graph.get_node(edge.to_id)
        if knob and knob.kind == "knob":
            return knob
    return None


def _range_from_knob(knob: EvidenceNode | None) -> dict | None:
    if knob is None:
        return None
    domain = knob.data.get("domain", {})
    result = {}
    if "minimum" in domain:
        result["minimum"] = domain["minimum"]
    if "maximum" in domain:
        result["maximum"] = domain["maximum"]
    if "unit" in domain:
        result["unit"] = domain["unit"]
    if result:
        return result
    if "candidates" in domain:
        return {"candidates": domain["candidates"]}
    return {"kind": domain.get("kind", "unspecified")}


def _agent_metadata_for_field(graph: EvidenceGraph, field_node: EvidenceNode) -> dict[str, Any]:
    ir_edges = _edges_from(graph, field_node.id, "field_maps_to_ir")
    ir_layer = "needs_review"
    schedule_points = []
    for edge in ir_edges:
        target = graph.get_node(edge.to_id)
        if target is None:
            continue
        if target.kind == "schedule_point":
            schedule_points.append(target.id)
        if "ir_layer" in target.data and target.data["ir_layer"] != "kernel":
            ir_layer = target.data["ir_layer"]
        elif target.id.startswith("ir:kernel:"):
            ir_layer = "kernel"

    feature_sources = [
        edge.from_id for edge in _edges_to(graph, field_node.id, "feature_derived_from")
    ]
    measurement_metrics = [
        edge.from_id.replace("metric:", "")
        for edge in _edges_to(graph, field_node.id, "metric_measures_field")
    ]

    return {
        "ir_layer": ir_layer,
        "schedule_points": sorted(set(schedule_points)),
        "feature_sources": sorted(set(feature_sources)),
        "measurement_metrics": sorted(set(measurement_metrics)),
        "replay_requirements": [
            "environment_fingerprint",
            "shape_signature",
            "dsl_version",
            "schedule_trace",
            "validator_results",
            "compile_result",
            "measurement_result",
            "failure_metadata",
        ],
    }
```

- [ ] **Step 4: Add agent metadata and knob ranges to schema fields**

In `_build_module_schemas`, after computing `has_knob`, add:

```python
            knob_node = _knob_for_field(graph, field_node.id)
            agent_metadata = _agent_metadata_for_field(graph, field_node)
```

Replace the `schemas[mod][field_name] = { ... }` block with:

```python
            field_spec = {
                "type": _infer_field_type(meaning),
                "searchable": has_knob,
                "editable_policy": _infer_editable_policy(field_node, has_knob),
                "source_cards": source_cards,
                "source_evidence": source_evidence if source_evidence else ["needs_evidence: true"],
                "meaning": meaning,
                "confidence": confidence,
                **agent_metadata,
            }
            if has_knob:
                knob_range = _range_from_knob(knob_node)
                if knob_range is not None:
                    field_spec["range"] = knob_range
            schemas[mod][field_name] = field_spec
```

- [ ] **Step 5: Add v0.4 artifact builders**

Add these functions above `synthesize`:

```python
def _build_ir_artifacts(graph: EvidenceGraph) -> dict[str, dict]:
    semantic_entities = [
        node.data for node in _nodes_by_kind(graph, "semantic_entity")
        if node.data.get("ir_layer") == "semantic"
    ]
    kernel_schedule_points = [
        {
            "id": node.id,
            "field": node.data.get("field_path", ""),
            "action": node.data.get("action", ""),
            "searchable": node.data.get("searchable", False),
            "guard_validators": sorted(edge.to_id for edge in _edges_from(graph, node.id, "schedule_point_guarded_by")),
        }
        for node in _nodes_by_kind(graph, "schedule_point")
    ]
    capabilities = [
        {"id": node.id, **node.data}
        for node in _nodes_by_kind(graph, "hardware_capability")
    ]
    metrics = [
        {"id": node.id, **node.data}
        for node in _nodes_by_kind(graph, "measurement_metric")
    ]
    features = [
        {"id": node.id, **node.data}
        for node in _nodes_by_kind(graph, "feature_source")
    ]
    tuning_record_fields = [
        {"id": node.id, **node.data}
        for node in _nodes_by_kind(graph, "tuning_record_field")
    ]

    return {
        "semantic_ir": {
            "version": "0.4",
            "kind": "ascend.attention.semantic_ir",
            "entities": semantic_entities,
        },
        "kernel_ir": {
            "version": "0.4",
            "kind": "ascend.attention.kernel_ir",
            "schedule_points": kernel_schedule_points,
        },
        "hardware_contract": {
            "version": "0.4",
            "kind": "ascend.attention.hardware_contract",
            "capabilities": capabilities,
        },
        "execution_feedback": {
            "version": "0.4",
            "kind": "ascend.attention.execution_feedback",
            "metrics": metrics,
            "features": features,
            "tuning_record_fields": tuning_record_fields,
        },
    }


def _build_search_artifacts(graph: EvidenceGraph) -> dict[str, dict]:
    schedule_points = []
    for node in _nodes_by_kind(graph, "schedule_point"):
        field_id = f"field:{node.data.get('field_path', '')}"
        field_node = graph.get_node(field_id)
        knob = _knob_for_field(graph, field_id)
        item = {
            "id": node.id,
            "field": node.data.get("field_path", ""),
            "action": node.data.get("action", ""),
            "searchable": node.data.get("searchable", False),
            "source_knob": knob.data.get("name") if knob else None,
            "guard_validators": sorted(edge.to_id for edge in _edges_from(graph, node.id, "schedule_point_guarded_by")),
            "forbidden_moves": ["event_wait_reorder", "online_softmax_formula_edit", "lse_formula_edit"],
        }
        knob_range = _range_from_knob(knob)
        if knob_range is not None:
            item["range"] = knob_range
        if field_node is not None:
            item["meaning"] = field_node.data.get("meaning", "")
        schedule_points.append(item)

    return {
        "schedule_space": {
            "version": "0.4",
            "kind": "ascend.attention.schedule_space",
            "schedule_points": schedule_points,
        },
        "feature_schema": {
            "version": "0.4",
            "kind": "ascend.attention.feature_schema",
            "features": [{"id": node.id, **node.data} for node in _nodes_by_kind(graph, "feature_source")],
        },
        "measurement_schema": {
            "version": "0.4",
            "kind": "ascend.attention.measurement_schema",
            "metrics": [{"id": node.id, **node.data} for node in _nodes_by_kind(graph, "measurement_metric")],
        },
        "tuning_record_schema": {
            "version": "0.4",
            "kind": "ascend.attention.tuning_record_schema",
            "fields": [{"id": node.id, **node.data} for node in _nodes_by_kind(graph, "tuning_record_field")],
        },
    }
```

- [ ] **Step 6: Write new artifacts from `synthesize`**

In `synthesize`, after `shadows = _build_shadow_dsl(graph)`, add:

```python
    ir_artifacts = _build_ir_artifacts(graph)
    search_artifacts = _build_search_artifacts(graph)
```

After writing `field_policy.yaml`, add:

```python
    _write(output_dir / "ir" / "semantic_ir.yaml", _ydump(ir_artifacts["semantic_ir"]))
    _write(output_dir / "ir" / "kernel_ir.yaml", _ydump(ir_artifacts["kernel_ir"]))
    _write(output_dir / "ir" / "hardware_contract.yaml", _ydump(ir_artifacts["hardware_contract"]))
    _write(output_dir / "ir" / "execution_feedback.yaml", _ydump(ir_artifacts["execution_feedback"]))

    _write(output_dir / "search" / "schedule_space.yaml", _ydump(search_artifacts["schedule_space"]))
    _write(output_dir / "search" / "feature_schema.yaml", _ydump(search_artifacts["feature_schema"]))
    _write(output_dir / "search" / "measurement_schema.yaml", _ydump(search_artifacts["measurement_schema"]))
    _write(output_dir / "search" / "tuning_record.schema.yaml", _ydump(search_artifacts["tuning_record_schema"]))
```

In the returned dictionary, add:

```python
        "ir": ["semantic_ir.yaml", "kernel_ir.yaml", "hardware_contract.yaml", "execution_feedback.yaml"],
        "search": ["schedule_space.yaml", "feature_schema.yaml", "measurement_schema.yaml", "tuning_record.schema.yaml"],
```

- [ ] **Step 7: Run synthesizer tests**

Run:

```bash
python -m pytest skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py -v
```

Expected: all synthesizer tests pass.

- [ ] **Step 8: Commit synthesizer changes**

```bash
git add skills/stage2-dsl-ontology-builder/tests/test_synthesizer.py \
        skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py
git commit -m "feat(stage2): synthesize agent-ready DSL contracts"
```

## Task 3: Verifier Agent Readiness Gate

**Files:**
- Modify: `skills/stage2-dsl-ontology-builder/tests/test_verifier.py`
- Modify: `skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py`

- [ ] **Step 1: Write failing verifier tests**

Append this to `skills/stage2-dsl-ontology-builder/tests/test_verifier.py`:

```python
import yaml


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
```

- [ ] **Step 2: Run verifier tests and verify the new tests fail**

Run:

```bash
python -m pytest skills/stage2-dsl-ontology-builder/tests/test_verifier.py -v
```

Expected: the new tests fail because `agent_readiness` is not present.

- [ ] **Step 3: Add verifier helpers for schema and agent artifacts**

In `skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py`, add these helpers above `verify`:

```python
def _load_all_schema_fields(stage2_dir: Path) -> list[dict[str, Any]]:
    fields = []
    schema_dir = stage2_dir / "schema" / "modules"
    if not schema_dir.exists():
        return fields
    for schema_file in schema_dir.glob("*.yaml"):
        data = _load_yaml_file(schema_file)
        if not isinstance(data, dict):
            continue
        for module_name, module_fields in data.items():
            if not isinstance(module_fields, dict):
                continue
            for field_name, spec in module_fields.items():
                if isinstance(spec, dict):
                    fields.append({
                        "module": module_name,
                        "name": field_name,
                        "path": f"{module_name}.{field_name}",
                        "spec": spec,
                    })
    return fields


def _agent_issue(severity: str, category: str, message: str, remediation: str) -> dict[str, str]:
    return {
        "severity": severity,
        "category": category,
        "message": message,
        "remediation": remediation,
    }


def _required_tuning_record_names(stage2_dir: Path) -> set[str]:
    path = stage2_dir / "search" / "tuning_record.schema.yaml"
    data = _load_yaml_file(path)
    if not isinstance(data, dict):
        return set()
    return {item.get("name", "") for item in data.get("fields", []) if isinstance(item, dict)}
```

- [ ] **Step 4: Add agent readiness checks**

Add this function above `verify`:

```python
def _check_agent_readiness(graph: EvidenceGraph, stage2_dir: Path) -> dict[str, Any]:
    scores = {
        "ir_layer_mapping": 20,
        "schedule_space_quality": 25,
        "hardware_contract_coverage": 20,
        "feedback_contract_completeness": 20,
        "replayability": 15,
    }
    issues: list[dict[str, str]] = []
    hard_failures: list[str] = []

    fields = _load_all_schema_fields(stage2_dir)
    schedule_data = _load_yaml_file(stage2_dir / "search" / "schedule_space.yaml") or {}
    hardware_data = _load_yaml_file(stage2_dir / "ir" / "hardware_contract.yaml") or {}
    feedback_data = _load_yaml_file(stage2_dir / "ir" / "execution_feedback.yaml") or {}

    schedule_points = schedule_data.get("schedule_points", []) if isinstance(schedule_data, dict) else []
    schedule_fields = {item.get("field") for item in schedule_points if isinstance(item, dict)}
    capability_names = {item.get("name") for item in hardware_data.get("capabilities", []) if isinstance(item, dict)}
    metrics = {item.get("name") for item in feedback_data.get("metrics", []) if isinstance(item, dict)}

    for field in fields:
        spec = field["spec"]
        if "ir_layer" not in spec or spec.get("ir_layer") == "needs_review":
            scores["ir_layer_mapping"] -= 3
            issues.append(_agent_issue(
                "warning", "ir",
                f"Field {field['path']} has no resolved IR layer",
                "Add an ir_layer mapping rule or mark the source field for review",
            ))

        if spec.get("searchable") and field["path"] not in schedule_fields:
            scores["schedule_space_quality"] -= 5
            message = f"Searchable field {field['path']} is missing from schedule_space"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Add the field to search/schedule_space.yaml"))

        if spec.get("searchable") and not any(key in spec for key in ("range", "candidates", "enum")):
            scores["schedule_space_quality"] -= 5
            message = f"Searchable field {field['path']} has no range, candidates, or enum"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Map the source knob domain into the schema field"))

        if spec.get("ir_layer") == "hardware" and not capability_names:
            scores["hardware_contract_coverage"] -= 5
            message = f"Hardware field {field['path']} has no hardware contract"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "hardware", message, "Add a hardware capability entry"))

        lowered_path = field["path"].lower()
        if spec.get("searchable") and ("softmax" in lowered_path or "lse" in lowered_path or "formula" in lowered_path):
            scores["schedule_space_quality"] -= 8
            message = f"Unsafe formula field {field['path']} is searchable"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Mark formula fields fixed"))

    for item in schedule_points:
        if not isinstance(item, dict):
            continue
        if not item.get("guard_validators"):
            scores["schedule_space_quality"] -= 5
            message = f"Schedule point has no validator guard: {item.get('id', item.get('field', 'unknown'))}"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Attach at least one constraint, risk, or mandatory validator"))
        if item.get("searchable") and not any(key in item for key in ("range", "candidates", "enum")):
            scores["schedule_space_quality"] -= 4
            message = f"Searchable schedule point has no domain: {item.get('id', item.get('field', 'unknown'))}"
            hard_failures.append(message)
            issues.append(_agent_issue("error", "schedule", message, "Add range, candidates, or enum"))

    if not capability_names:
        scores["hardware_contract_coverage"] = 0
        hard_failures.append("Hardware contract has no capabilities")
        issues.append(_agent_issue("error", "hardware", "Hardware contract has no capabilities", "Generate ir/hardware_contract.yaml capabilities"))

    if not metrics:
        scores["feedback_contract_completeness"] = 0
        hard_failures.append("Execution feedback has no metrics")
        issues.append(_agent_issue("error", "feedback", "Execution feedback has no metrics", "Generate metrics in ir/execution_feedback.yaml"))

    required_record_fields = {
        "environment_fingerprint",
        "shape_signature",
        "dsl_version",
        "schedule_trace",
        "validator_results",
        "compile_result",
        "measurement_result",
        "failure_metadata",
    }
    missing_record_fields = required_record_fields - _required_tuning_record_names(stage2_dir)
    if missing_record_fields:
        scores["replayability"] -= min(15, len(missing_record_fields) * 3)
        message = f"Tuning record schema missing fields: {', '.join(sorted(missing_record_fields))}"
        hard_failures.append(message)
        issues.append(_agent_issue("error", "replay", message, "Add required replay fields to search/tuning_record.schema.yaml"))

    normalized_scores = {key: max(0, value) for key, value in scores.items()}
    total = sum(normalized_scores.values())
    status = "fail" if hard_failures else "pass" if total >= 85 else "warn" if total >= 70 else "fail"
    return {
        "status": status,
        "score": total,
        "scores": normalized_scores,
        "hard_failures": hard_failures,
        "issues": issues,
    }
```

- [ ] **Step 5: Integrate agent readiness into `verify`**

Inside `verify`, after the existing shadow DSL coverage check, add:

```python
    agent_readiness = _check_agent_readiness(graph, stage2_dir)
```

Replace the status computation with:

```python
    status = "pass" if total >= 85 and not hard_failures and agent_readiness["status"] != "fail" else "warn" if total >= 70 and not agent_readiness["hard_failures"] else "fail"
```

In the `result` dictionary, add:

```python
        "agent_readiness": agent_readiness,
```

After writing `quality_gate.md`, add:

```python
    readiness_md = ["# Stage 2 Agent Readiness", "", f"Status: **{agent_readiness['status']}**", f"Score: **{agent_readiness['score']}/100**", "", "## Scores", ""]
    for key, value in agent_readiness["scores"].items():
        readiness_md.append(f"- {key}: {value}")
    readiness_md += ["", "## Issues", ""]
    readiness_md += [
        f"- [{issue['severity']}] ({issue['category']}) {issue['message']}"
        for issue in agent_readiness["issues"]
    ] or ["- No issues found."]
    (stage2_dir / "review" / "agent_readiness.md").write_text("\n".join(readiness_md) + "\n", encoding="utf-8")
```

- [ ] **Step 6: Run verifier tests**

Run:

```bash
python -m pytest skills/stage2-dsl-ontology-builder/tests/test_verifier.py -v
```

Expected: all verifier tests pass.

- [ ] **Step 7: Commit verifier changes**

```bash
git add skills/stage2-dsl-ontology-builder/tests/test_verifier.py \
        skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py
git commit -m "feat(stage2): add agent readiness quality gate"
```

## Task 4: Integration and Shim Regression Coverage

**Files:**
- Modify: `skills/stage2-dsl-ontology-builder/tests/test_integration.py`
- Create: `skills/stage2-dsl-ontology-builder/tests/test_shims.py`

- [ ] **Step 1: Extend integration test for v0.4 outputs**

In `skills/stage2-dsl-ontology-builder/tests/test_integration.py`, after the existing assertions for `atdsl.schema.yaml`, add:

```python
    assert (output_dir / "ir" / "semantic_ir.yaml").exists()
    assert (output_dir / "ir" / "kernel_ir.yaml").exists()
    assert (output_dir / "ir" / "hardware_contract.yaml").exists()
    assert (output_dir / "ir" / "execution_feedback.yaml").exists()
    assert (output_dir / "search" / "schedule_space.yaml").exists()
    assert (output_dir / "search" / "feature_schema.yaml").exists()
    assert (output_dir / "search" / "measurement_schema.yaml").exists()
    assert (output_dir / "search" / "tuning_record.schema.yaml").exists()
```

After `result = verify(graph, output_dir)`, add:

```python
    assert "agent_readiness" in result
    assert (output_dir / "review" / "agent_readiness.md").exists()
```

- [ ] **Step 2: Add shim regression tests**

Create `skills/stage2-dsl-ontology-builder/tests/test_shims.py`:

```python
import json
import subprocess
import sys
from pathlib import Path


def test_bootstrap_shim_generates_v04_outputs():
    skill_dir = Path(__file__).parent.parent
    fixtures = skill_dir / "tests" / "fixtures"
    output_dir = Path("/tmp/test_stage2_bootstrap_shim_v04")

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
    assert (output_dir / "ir" / "semantic_ir.yaml").exists()
    assert (output_dir / "search" / "schedule_space.yaml").exists()


def test_quality_shim_preserves_quality_gate_json():
    skill_dir = Path(__file__).parent.parent
    fixtures = skill_dir / "tests" / "fixtures"
    output_dir = Path("/tmp/test_stage2_quality_shim_v04")

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
```

- [ ] **Step 3: Run integration and shim tests**

Run:

```bash
python -m pytest skills/stage2-dsl-ontology-builder/tests/test_integration.py skills/stage2-dsl-ontology-builder/tests/test_shims.py -v
```

Expected: integration test passes or skips if real Stage 1 data is absent; shim tests pass.

- [ ] **Step 4: Commit integration coverage**

```bash
git add skills/stage2-dsl-ontology-builder/tests/test_integration.py \
        skills/stage2-dsl-ontology-builder/tests/test_shims.py
git commit -m "test(stage2): cover v04 integration and shims"
```

## Task 5: Skill Documentation and Contracts

**Files:**
- Modify: `skills/stage2-dsl-ontology-builder/SKILL.md`
- Modify: `skills/stage2-dsl-ontology-builder/README.md`
- Modify: `skills/stage2-dsl-ontology-builder/references/stage2_workflow.md`
- Modify: `skills/stage2-dsl-ontology-builder/references/output_contract.md`
- Modify: `skills/stage2-dsl-ontology-builder/references/schema_design_rules.md`
- Modify: `skills/stage2-dsl-ontology-builder/references/validators_and_lowering.md`
- Modify: `skills/stage2-dsl-ontology-builder/references/quality_gate.md`
- Modify: `skills/stage2-dsl-ontology-builder/agents/openai.yaml`

- [ ] **Step 1: Update `SKILL.md` required output structure**

In `skills/stage2-dsl-ontology-builder/SKILL.md`, add this under `stage2_outputs/` after `ontology/`:

```text
  ir/
    semantic_ir.yaml
    kernel_ir.yaml
    hardware_contract.yaml
    execution_feedback.yaml

  search/
    schedule_space.yaml
    feature_schema.yaml
    measurement_schema.yaml
    tuning_record.schema.yaml
```

In the hard constraints section, add:

```markdown
- Treat v0.4 artifacts as contracts, not executable compiler output.
- Every searchable field must appear in `search/schedule_space.yaml` with a finite domain and validator guard.
- Every schedule point must be guarded by a constraint, risk-derived validator, or mandatory validator.
- Hardware-sensitive fields must link to `ir/hardware_contract.yaml`.
- Tuning records must include environment fingerprint, shape signature, DSL version, schedule trace, validation result, compile result, measurement result, and failure metadata.
- Do not claim benchmark results from `measurement_schema.yaml`; it describes future measurements only.
```

- [ ] **Step 2: Update `README.md` quick start**

Append this section to `skills/stage2-dsl-ontology-builder/README.md`:

```markdown
## Stage 2 v0.4 agent-ready contracts

The synthesizer now emits additional contracts for later agent search and replay:

- `ir/semantic_ir.yaml`
- `ir/kernel_ir.yaml`
- `ir/hardware_contract.yaml`
- `ir/execution_feedback.yaml`
- `search/schedule_space.yaml`
- `search/feature_schema.yaml`
- `search/measurement_schema.yaml`
- `search/tuning_record.schema.yaml`

These files describe the DSL action space, hardware assumptions, feature schema, metric schema, and replay record format. They do not compile kernels or report measured performance.
```

- [ ] **Step 3: Update `references/output_contract.md`**

Append:

````markdown
## Stage 2 v0.4 agent-ready outputs

Additional directories:

```text
stage2_outputs/
  ir/
    semantic_ir.yaml
    kernel_ir.yaml
    hardware_contract.yaml
    execution_feedback.yaml
  search/
    schedule_space.yaml
    feature_schema.yaml
    measurement_schema.yaml
    tuning_record.schema.yaml
```

Per-field schema entries may include:

```yaml
ir_layer: semantic|kernel|hardware|execution_feedback|needs_review
schedule_points: []
feature_sources: []
measurement_metrics: []
replay_requirements: []
```

`quality_gate.json` may include:

```json
{
  "agent_readiness": {
    "status": "pass|warn|fail",
    "score": 0,
    "scores": {
      "ir_layer_mapping": 0,
      "schedule_space_quality": 0,
      "hardware_contract_coverage": 0,
      "feedback_contract_completeness": 0,
      "replayability": 0
    },
    "hard_failures": [],
    "issues": []
  }
}
```
````

- [ ] **Step 4: Update workflow, schema, validator, and quality references**

Append this to `references/stage2_workflow.md`:

```markdown
## Stage 2 v0.4 four-layer contract

Stage 2 also emits four agent-facing layers:

- Semantic IR: pure operator meaning, shape, dtype, layout intent, and fixed formulas.
- Kernel IR: schedulable objects such as loops, tiles, buffers, memory scopes, and pipeline stages.
- Hardware contract: target-sensitive capacities, memory spaces, alignment, and intrinsic assumptions.
- Execution feedback: feature schema, metric schema, schedule trace, and tuning record format.
```

Append this to `references/schema_design_rules.md`:

```markdown
## v0.4 IR-layer metadata

Every generated field should declare an `ir_layer`.

- `semantic`: operator meaning and fixed math.
- `kernel`: schedulable implementation choices.
- `hardware`: target capability or capacity assumptions.
- `execution_feedback`: metric, feature, trace, or replay fields.
- `needs_review`: field exists but layer inference was not reliable.
```

Append this to `references/validators_and_lowering.md`:

```markdown
## v0.4 schedule guards and replay

Every schedule point must declare guard validators before it can be searched. Lowering specs should declare which feature, measurement, or replay fields they need so later stages can reproduce schedule attempts.
```

Append this to `references/quality_gate.md`:

```markdown
## Agent readiness

The verifier reports `agent_readiness` in addition to the legacy score. Hard failures include searchable fields without domains, schedule points without guards, hardware-sensitive fields without hardware contracts, unsafe searchable formula fields, and tuning records missing replay-critical fields.
```

- [ ] **Step 5: Update agent role hints**

In `skills/stage2-dsl-ontology-builder/agents/openai.yaml`, add these roles under `agent_roles`:

```yaml
  - name: IR Contract Agent
    tool: scripts/stage2_synthesizer.py
    input: .evidence_graph.json
    output: ir/*.yaml
    purpose: Generate semantic IR, kernel IR, hardware contract, and execution feedback contracts
  - name: Search Contract Agent
    tool: scripts/stage2_synthesizer.py
    input: .evidence_graph.json
    output: search/*.yaml
    purpose: Generate schedule space, feature schema, measurement schema, and tuning record schema
  - name: Agent Readiness Verifier
    tool: scripts/stage2_verifier.py
    input: .evidence_graph.json + stage2_outputs
    output: review/agent_readiness.md
    purpose: Check action-space guards, hardware coverage, feedback completeness, and replayability
```

- [ ] **Step 6: Commit documentation changes**

```bash
git add skills/stage2-dsl-ontology-builder/SKILL.md \
        skills/stage2-dsl-ontology-builder/README.md \
        skills/stage2-dsl-ontology-builder/references/stage2_workflow.md \
        skills/stage2-dsl-ontology-builder/references/output_contract.md \
        skills/stage2-dsl-ontology-builder/references/schema_design_rules.md \
        skills/stage2-dsl-ontology-builder/references/validators_and_lowering.md \
        skills/stage2-dsl-ontology-builder/references/quality_gate.md \
        skills/stage2-dsl-ontology-builder/agents/openai.yaml
git commit -m "docs(stage2): document agent-ready DSL contracts"
```

## Task 6: Full Verification and Final Cleanup

**Files:**
- Verify: `skills/stage2-dsl-ontology-builder/tests/*`
- Verify: `skills/stage2-dsl-ontology-builder/scripts/*`
- Verify: `skills/stage2-dsl-ontology-builder/references/*`

- [ ] **Step 1: Run all Stage 2 skill tests**

Run:

```bash
python -m pytest skills/stage2-dsl-ontology-builder/tests -v
```

Expected: all tests pass, with only intentional skips for missing real Stage 1 artifacts.

- [ ] **Step 2: Run the full pipeline manually on fixtures**

Run:

```bash
python skills/stage2-dsl-ontology-builder/scripts/stage2_parser.py \
  --input skills/stage2-dsl-ontology-builder/tests/fixtures \
  --output /tmp/stage2_v04_manual/.evidence_graph.json
python skills/stage2-dsl-ontology-builder/scripts/stage2_synthesizer.py \
  --evidence-graph /tmp/stage2_v04_manual/.evidence_graph.json \
  --output /tmp/stage2_v04_manual
python skills/stage2-dsl-ontology-builder/scripts/stage2_verifier.py \
  --evidence-graph /tmp/stage2_v04_manual/.evidence_graph.json \
  --stage2-dir /tmp/stage2_v04_manual
```

Expected: parser reports a graph saved, synthesizer reports generated files, verifier prints JSON containing `overall_status` and `agent_readiness`.

- [ ] **Step 3: Inspect generated v0.4 files**

Run:

```bash
test -f /tmp/stage2_v04_manual/ir/semantic_ir.yaml
test -f /tmp/stage2_v04_manual/ir/kernel_ir.yaml
test -f /tmp/stage2_v04_manual/ir/hardware_contract.yaml
test -f /tmp/stage2_v04_manual/ir/execution_feedback.yaml
test -f /tmp/stage2_v04_manual/search/schedule_space.yaml
test -f /tmp/stage2_v04_manual/search/feature_schema.yaml
test -f /tmp/stage2_v04_manual/search/measurement_schema.yaml
test -f /tmp/stage2_v04_manual/search/tuning_record.schema.yaml
test -f /tmp/stage2_v04_manual/review/agent_readiness.md
```

Expected: all `test -f` commands exit successfully.

- [ ] **Step 4: Review working tree**

Run:

```bash
git status --short
```

Expected: only intentional changes from the implementation branch are present. Existing untracked user artifacts under `artifacts/`, `docs/superpowers/dsl_deep_report.md`, and `dsl/reports/` should remain unmodified unless the user explicitly asked to track them.

- [ ] **Step 5: Commit final cleanup if needed**

If verification changes produced small documentation or test fixes, commit them:

```bash
git add skills/stage2-dsl-ontology-builder
git commit -m "chore(stage2): finalize agent-ready DSL v04"
```

If no files changed after the previous commits, do not create an empty commit.
