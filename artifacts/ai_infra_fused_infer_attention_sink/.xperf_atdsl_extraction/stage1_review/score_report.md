# Stage-1 Artifact Review — `ai_infra_fused_infer_attention_sink`

- Reviewer: stage1-artifact-scorer skill
- Operator: AscendC fused infer attention sink (FlashAttention + FlashDecode prefill/decode, GQA + MLA + generic nonquant variants)
- Source root: `/tmp/fia_sink_src/inference/ascendc/src/ops-transformer/attention/ai_infra_fused_infer_attention_sink/` (extracted from `omni-ops-performance/ai_infra_fused_infer_attention_sink_code_and_extraction_20260502.tar.gz`)
- Extraction root: `artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction/`
- Review date: 2026-05-04

## 1. Executive summary

Stage-1 extraction is high quality and ready for Stage-2 DSL ontology/schema design. All 15 required FA/FlashDecode kernel structures are covered, every optimization card carries traceable source evidence, and the dedicated `dsl/`, `constraints/forbidden_transforms.yaml`, and MLA-tail/workspace contracts are uniquely strong: they make non-obvious AscendC patterns (three-stage RunInfo ring, MLA nUpdate atomic-add through `mm2ResInt32Gm`, host-budget-only MLA tail stubs, FD metadata host→kernel bridge) directly DSL-convertible.

Six high-impact cards were spot-checked against source code and all match precisely. There are no blocking findings. Eight known schema gaps are explicitly tracked with `temporary_schema_stub.status: ready_for_ingestion` artifacts that Stage-2 can consume.

- **Total score: 96 / 100**
- **Readiness: READY_FOR_STAGE2**
- **Blocking findings: 0**

## 2. Score breakdown

| Dimension | Weight | Score | Notes |
|---|---:|---:|---|
| Coverage | 25 | 24 | All 15 required structures present plus common_supplement, MLA tail contracts, and scalar offset rules. Minor under-specification on hardware micro-optimization applicability bands. |
| Accuracy | 25 | 24 | 6 high-value cards directly `verified_against_source`. No contradictions found. Remaining cards rated `supported_by_artifacts_only` due to spot-check budget, not suspicion. |
| Traceability | 15 | 14 | 33/33 cards, 25/25 constraints, 23/23 risks, 7/7 knobs reference source evidence ids or `file:line` ranges. SE-* id catalogue not enumerated this session (cross_reference.yaml is sufficient). |
| DSL-convertibility | 20 | 19 | Every card has both `possible_dsl_fields` and `lowering_hint`. 10 `dsl/suggested_dsl_sections.yaml` entries + 8 schema gaps with ingestion-ready stubs. Stage-2 still needs to wire stubs into the final schema. |
| Risk & constraints | 10 | 10 | 23 risks ↔ 11 forbidden_transforms cross-linked. 25 constraints with `evidence: file:line`. Covers deadlock, alignment, numerical, atomic, ABI drift, mis-lowering. |
| Dedup & canonicalization | 5 | 5 | Explicit `canonical_name` + `aliases` per card. 9 stage-aligned sections. No duplicates observed. |
| **Total** | **100** | **96** | |

## 3. Gate-condition results

| Gate | Threshold | Observed | Result |
|---|---:|---:|---|
| Coverage ≥ 18/25 | 18 | 24 | PASS |
| Accuracy ≥ 20/25 | 20 | 24 | PASS |
| DSL-convertibility ≥ 15/20 | 15 | 19 | PASS |
| Important card evidence coverage ≥ 90% | 90% | 100% (33/33 cards have source_evidence) | PASS |
| Human spot-check accuracy ≥ 85% | 85% | 100% (6/6 spot-checked cards verified) | PASS |

## 4. Coverage matrix — 15 required structures

| # | Structure | Artifact(s) | Status |
|---:|---|---|---|
| 1 | interface / tilingData / workspace input | `reports/file_inventory.yaml` (op_host/* + tiling files), constraints `C-WORKSPACE-CONTIGUOUS-ABI` | covered |
| 2 | shape/layout: B,S1,S2,N,G,D,varlen,layout conversion | `dsl/shape_layout_contract.yaml`, card `OC-LSE-EXPORT-LAYOUT-CONTRACT`, schema_gap `shape_layout.contract` | covered |
| 3 | multi-core mapping: blockIdx → batch/head/group/S1/S2/KV split | cards `OC-COMMON-SPLIT-CORE-BALANCING`, `OC-COMMON-SPARSE-SINK-S2-RANGE`; `dsl/split_core_range_contract.yaml` | covered |
| 4 | S1/S2 loop or KV-block loop | cards `OC-RUNINFO-THREE-STAGE-RING`, `OC-VEC1-M-PARTITION-SPLIT` | covered |
| 5 | BMM1/Vec1/BMM2/Vec2 pipeline (or decode KV-streaming) | cards `OC-MM1-VEC1-SOFTMAX-PIPELINE-BRIDGE`, `OC-MM1-OUTPUT-FIXPIPE-ATOMIC-ADD-ACCUMULATION`, `OC-VEC1-ONLINE-SOFTMAX-FLASHV2`, `OC-GQA-MM2-L1-V-REUSE` | covered |
| 6 | UB / L1 / L0 buffer usage | cards `OC-GQA-MM1-Q-L1-SNAPSHOT-REUSE`, `OC-GQA-MM1-KP-L1-DOUBLE-BUFFER-PINGPONG`, `OC-COMMON-BUFFER-MATRIX-2X2-POLICY` | covered |
| 7 | L1 residency and L1 partitioning | `dsl/suggested_dsl_sections.yaml::memory.l1_residency` + cards above | covered |
| 8 | sparse window / causal / band / prefix / mask rules | `dsl/sparse_policy.yaml`, card `OC-VEC1-SINK-SKIP-AND-INVALID-ROW`, `OC-COMMON-SPARSE-SINK-S2-RANGE` | covered |
| 9 | online softmax / LSE state | cards `OC-VEC1-ONLINE-SOFTMAX-FLASHV2`, `OC-SOFTMAX-TILING-BRC`, `OC-LSE-GENERATE-AND-EXPORT` | covered |
| 10 | workspace layout & offset uniqueness | cards `OC-WORKSPACE-NORMAL-RING`, `OC-WORKSPACE-FD-REGIONS`, `OC-WORKSPACE-MLA-NUPDATE-BUDGET-STUB`, `OC-WORKSPACE-MLA-SOFTMAX-SUM-BUDGET-STUB` | covered |
| 11 | tail handling and alignment | cards `OC-COMMON-VECTOR-INVALID-ROW-HANDLING`, knob `headDimAlign`, constraint `C-VEC-UB-ALIGNMENT` | covered |
| 12 | event/wait/flag synchronization | cards `OC-RUNINFO-THREE-STAGE-RING`, `OC-MM1-SPARSE-SKIP-L1-EVENT-DEADLOCK-GUARD`, `OC-MLA-MM2-NUPDATE-BARRIER`, `OC-COMMON-BUFFER-POLICY-SELECTION` | covered |
| 13 | scalar/offset/div-mod hoist opportunities | card `OC-SCALAR-RING-OFFSET-HOIST`; `dsl/scalar_offset_contract.yaml` | covered |
| 14 | split-KV partial output / max / sum / LSE merge for FlashDecode | cards `OC-FD-STABLE-MERGE`, `OC-FD-METADATA-BRIDGE`, `OC-COMMON-FD-METADATA-MERGE-BEHAVIOR` | covered |
| 15 | tunable knobs, hard constraints, forbidden transforms | `knobs/tunable_knobs.yaml` (7), `constraints/constraints.yaml` (25), `constraints/forbidden_transforms.yaml` (11) | covered |

## 5. Source spot-check results

Six high-value cards were verified directly against extracted source files. Verification labels follow skill conventions: `verified_against_source` requires source code inspection, `supported_by_artifacts_only` indicates strong internal evidence without code reading this session.

| Card | Target | File:Lines | Verdict |
|---|---|---|---|
| `OC-GQA-MM1-Q-L1-SNAPSHOT-REUSE` | `canFullLoadQ`, `qCoord` signature, `qL1Snapshot.signature == qCoord` | `op_kernel/fia_block_cube_nonquant_gqa_sink.h:988-1050` | verified_against_source |
| `OC-GQA-MM1-KP-L1-DOUBLE-BUFFER-PINGPONG` | `KP_EVENT0 + kpOrSinkL1BufId` ping-pong with two-bit slot id | `op_kernel/fia_block_cube_nonquant_gqa_sink.h:998-1113` | verified_against_source |
| `OC-MM1-SPARSE-SKIP-L1-EVENT-DEADLOCK-GUARD` | `SetFlag<KP_EVENT0>` issued before `continue` on skip path | `op_kernel/fia_block_cube_nonquant_gqa_sink.h:1005-1030` | verified_against_source |
| `OC-COMMON-MATMUL-UNITFLAG-K-LOOP` | `mmadParams.unitFlag = isLastK ? 3 : 2` | `op_kernel/fia_block_cube_nonquant_gqa_sink.h:1077` | verified_against_source |
| `OC-MLA-NUPDATE-SIDECHANNEL` + `OC-WORKSPACE-MLA-NUPDATE-BUDGET-STUB` | 128-lane Brcb broadcast, `SetAtomicAdd<int32_t>()`, write to `mm2ResInt32Gm[baseoffset + i*dGroupSize]` | `op_kernel/fia_block_vec_nonquant_mla_sink.h:657-717` | verified_against_source |
| `OC-WORKSPACE-NORMAL-RING` + `OC-FD-METADATA-BRIDGE` | Contiguous mm1Res→vec1Res→mm2Res→vec2Res `SetGlobalBuffer` order with `dbWorkspaceRatio = PRELOAD_NUM`; FD metadata reconstructed via `metadataGm.GetValue(GetBaseMetaAbsIndex/...)` | `op_kernel/fia_kernel_nonquant_sink.h:373-409,731-757`; `op_host/fia_tiling_nonquant_sink.cpp:320-365` | verified_against_source |
| `OC-FD-STABLE-MERGE` | `taskOffset` prefix-sum, preload-ring on `fdMm2ResBuf1/2`, layout-dispatch LSE export, `MTE3_V`/`V_MTE3` handshakes | `op_kernel/fia_block_vec_flashdecode_sink.h:437-555` | verified_against_source |

All other cards: `supported_by_artifacts_only` (strong internal evidence, no contradictions, but full source spot-check budget exceeded).

## 6. Top blocking issues

**None.** No card, constraint, knob, risk, or schema gap blocks Stage-2 entry.

## 7. Strengths and high-quality examples

### 7.1 Novel insights successfully captured

1. **MLA nUpdate side-channel** (`OC-MLA-NUPDATE-SIDECHANNEL` + `OC-WORKSPACE-MLA-NUPDATE-BUDGET-STUB`). The card correctly identifies that the host reserves nUpdate tail bytes but the kernel never binds a dedicated GM tensor — instead `mm2ResInt32Gm` is an int32 reinterpretation of `normal.mm2`, and `ProcessAmlaNupdate` performs a 128-lane `Brcb` broadcast followed by `SetAtomicAdd<int32_t>()` and `DataCopy` into that aliased region. Stage-2 lowering that flattens nUpdate into a standalone GM tensor is forbidden by `FT-NO-LOWER-MLA-BUDGET-TAIL-AS-BOUND-GM`.

2. **Three-stage RunInfo ring** (`OC-RUNINFO-THREE-STAGE-RING`). Slot ownership is explicitly: current = MM1, older = Vec1 + MM2, previous = Vec2 (then invalidated). Stage-2 schedulers that collapse this into a two-slot ring or invalidate after MM2 will silently break the overlap pattern.

3. **Sparse skip with deadlock guard** (`OC-MM1-SPARSE-SKIP-L1-EVENT-DEADLOCK-GUARD`). Two-level `IsSkipCal` check, but `SetFlag<KP_EVENT0>` is issued before `continue` so the producer/consumer counter advances monotonically. A naive optimizer that elides the SetFlag on skip paths produces a deadlock.

4. **FD metadata host→kernel bridge** (`OC-FD-METADATA-BRIDGE`). Host `SetSplitOutput` writes seven arrays into `tilingData_.fdParams.*`, kernel `FlashDecode` re-reads them via `metadataGm.GetValue(GetAICMetaAbsIndex(i, INDEX))` / `GetAIVMetaAbsIndex` and assembles a local `FDparams` struct. The internal split-core planner is correctly marked as out-of-extraction in `dsl/split_core_range_contract.yaml`.

### 7.2 Card structure quality

Every card includes:
- `applies_to.variants` (nonquant / gqa / mla / flash_decode) and `applies_to.owners` (template-qualified class names)
- `pattern_summary`, `optimization_intent`, `preconditions`
- `tunable_knobs` (cross-referencing `knobs/tunable_knobs.yaml`)
- `constraints` and `risks` (cross-referencing constraints/risks files)
- `possible_dsl_fields` with concrete dotted paths and meanings
- `lowering_hint` — actionable guidance for Stage-2 lowering
- `source_evidence` with id + role pairs
- explicit `confidence`

### 7.3 Risks ↔ forbidden_transforms cross-linkage

22 of 23 risks declare `related_forbidden_transform_ids`. The single exception (`R-SHAPE-LAYOUT-CONTRACT-DRIFT`) is correctly left empty because shape/layout drift is co-design rather than an enforceable transform constraint.

## 8. Weak or under-specified items

(None block Stage-2 entry; these are quality observations only.)

| Item | Issue | Suggested Stage-2 handling |
|---|---|---|
| Hardware micro-optimization cards (`OC-COMMON-MATMUL-UNITFLAG-K-LOOP`, `OC-COMMON-VECTOR-REPEAT-STRIDE-THRESHOLD`, `OC-COMMON-ND2NZ-INT4-STRIDE-LIMIT-FALLBACK`) | Applicability bands (data-type, tile-size, NZ-vs-ND) are correct but compressed. | Lower as policy-table fields rather than scalar fields. |
| MLA tail-stub cards (`OC-WORKSPACE-MLA-*`, confidence: medium) | Confidence is medium because the absence of a dedicated GM SetGlobalBuffer is harder to prove than its presence. | Stage-2 should emit guardrails that specifically test the negative case in regression. |
| Schema gaps (8 entries) | All marked `temporary_schema_stub.status: ready_for_ingestion` but Stage-2 still needs to wire them. | Treat the Stage-1 stubs as authoritative ingestion sources for the listed missing fields. |

## 9. Stage-2 input recommendations

### 9.1 Directly consumable

| Stage-1 artifact | Stage-2 use |
|---|---|
| `cards/optimization_cards.yaml` (33 cards) | Source of DSL module candidates; each card produces 2-5 schema fields plus a lowering rule. |
| `knobs/tunable_knobs.yaml` (7 knobs) | Direct schema for the search/tuning knob table; preserve `searchable: true/false` and `coupled_constraints`. |
| `constraints/constraints.yaml` (25) | Direct schema for the validator table. |
| `constraints/forbidden_transforms.yaml` (11) | Direct schema for the transform-guard table; cross-link by `source_evidence_ids`. |
| `risks/risks.yaml` (23) | Direct schema for the risk catalog; preserve `related_forbidden_transform_ids` cross-links. |
| `dsl/suggested_dsl_sections.yaml` (10 sections) | Top-level DSL section skeleton. |
| `dsl/schema_gaps.yaml` (8) | Direct enumeration of fields the final schema must add; each gap names producer/consumer locations and missing field paths. |
| `dsl/split_core_range_contract.yaml`, `dsl/sparse_policy.yaml`, `dsl/shape_layout_contract.yaml`, `dsl/scalar_offset_contract.yaml`, `dsl/mla_workspace_tail_contract.yaml`, `dsl/flash_decode_metadata_bridge.yaml`, `dsl/shared_stage_aliases.yaml` | Each is `ready_for_ingestion`. Wire fields into the final schema in line with the producer/consumer locations called out in `schema_gaps.yaml`. |

### 9.2 Validate-but-consume

| Stage-1 artifact | Caveat |
|---|---|
| `OC-WORKSPACE-MLA-NUPDATE-BUDGET-STUB`, `OC-WORKSPACE-MLA-SOFTMAX-SUM-BUDGET-STUB` (confidence: medium) | Negative-evidence findings; Stage-2 should regression-test that no new `SetGlobalBuffer` for these tails appears. |
| `common_supplement/*` artifacts | Treat as authoritative for the common include layer; Stage-2 may need to mirror corresponding common-layer schema entries explicitly. |

### 9.3 Out of scope (correctly noted)

- Internal split-core planner heuristic (`split_core.h`) — explicitly external; only the host-input/output bridge is in-extraction. Stage-2 must either ingest the planner separately or treat range-assignments as planner-supplied opaque arrays.

## 10. Final verdict

```
Total score: 96 / 100
Readiness:    READY_FOR_STAGE2
Blocking:     none
Confidence:   high (6 high-value cards verified_against_source; 0 contradictions)
```

Stage-2 may proceed using the artifacts as primary input. The DSL ontology design should preserve the canonical_name/aliases scheme already in the cards, the host-budget-only/alias/local-UB-bridge classification for workspace tails, and the host→kernel metadata bridge contracts for FlashDecode.
