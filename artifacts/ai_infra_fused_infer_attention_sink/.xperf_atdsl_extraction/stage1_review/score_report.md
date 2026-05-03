# Stage-1 Artifact Review: ai_infra_fused_infer_attention_sink

**Score:** 94/100
**Readiness:** READY_FOR_STAGE2
**Stage-2 gate blocked:** no

## Executive Summary

Reviewed input: `artifacts/ai_infra_fused_infer_attention_sink/.xperf_atdsl_extraction`

Source root: `/mnt/workspace/omni-ops-performance/inference/ascendc/src/ops-transformer/attention/ai_infra_fused_infer_attention_sink`

The extraction is technically strong: the core GQA, MLA, FlashDecode, workspace, sparse, pipeline, split-core, and common-helper structures are present and source-aligned. Targeted source spot checks matched the high-risk facts for RunInfo scheduling, GQA L1 reuse, MLA nUpdate, FD stable merge, workspace ABI, split-core FD metadata, and common helper behavior. All 33 optimization cards now resolve to first-class source evidence records, so the Stage-2 important-card-evidence gate passes.

## Score Breakdown

| Dimension | Score | Weight | Judgement |
|---|---:|---:|---|
| Coverage | 24 | 25 | All 15 required attention-kernel structures are represented; minor deduction for index-only coverage of many non-critical helpers. |
| Accuracy | 24 | 25 | Operator and common-source spot checks matched inspected claims, including the newly added MM1, Vec1, LSE, and common-helper card evidence. |
| Traceability | 15 | 15 | 33 of 33 optimization cards have resolvable source evidence IDs with source file, symbol, line range, observed fact, and confidence. |
| DSL-convertibility | 18 | 20 | Cards, contracts, graphs, knobs, constraints, and risks are field-oriented and ready for Stage-2 schema/validator/lowering design. |
| Risk & constraints | 9 | 10 | Strong forbidden transforms and risks; only minor non-blocking deductions remain. |
| Dedup & canonicalization | 4 | 5 | Canonical names and aliases are good; FD metadata and common/operator cards still need parent-child modeling to avoid duplicate Stage-2 modules. |

## Gate Conditions

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Coverage | >= 18 / 25 | 24 / 25 | PASS |
| Accuracy | >= 20 / 25 | 24 / 25 | PASS |
| DSL-convertibility | >= 15 / 20 | 18 / 20 | PASS |
| Important card evidence coverage | >= 90% | 33 / 33 = 100.0% resolvable source evidence | PASS |
| Human spot-check accuracy | >= 85% if available | Not provided; AI source spot checks matched inspected facts | N/A |

All blocking gates pass. Stage-2 ingestion is unblocked.

## Evidence Coverage

- Optimization cards: 33
- Cards with resolvable source evidence: 33
- Coverage: 100.0%
- Previous blocker resolved: 15 cards cited 33 missing source evidence IDs; all 33 IDs now exist in `evidence/source_evidence.yaml`.

## Inventory

| Artifact class | Count / status |
|---|---:|
| Indexed functions | 616 |
| Deep function annotations | 134 |
| Brief annotations | 18 |
| Index annotations | 616 |
| File annotations | 38 |
| Optimization cards | 33 |
| Tunable knobs | 7 |
| Hard constraints | 25 |
| Risk records | 23 |
| Suggested DSL sections | 10 |
| Schema gaps | 8 |
| Dataflow graph | Present |
| Pipeline graph | Present |
| Memory lifetime | Present |
| Workspace layout | Present |

## Coverage Matrix

| Required structure | Status | Judgement |
|---|---|---|
| 1. Interface / tilingData / workspace input | Strong | API, host tiling, tiling metadata, workspace sizing, and kernel workspace binding are covered. |
| 2. Shape/layout: B, S1, S2, N, G, D, varlen, conversion | Strong | Shape/layout contract covers dense, TND/NTD, NZ/common axis maps, LSE/output layout paths, and tests. |
| 3. Multi-core mapping | Strong | Split-core range contract, host bridge, FD metadata arrays, and common split-core supplement are present. |
| 4. S1/S2 loop or KV-block loop | Strong | GQA, MLA, shared Vec, and FD annotations expose S2/KV/task loops and tail rules. |
| 5. BMM1 / Vec1 / BMM2 / Vec2 or decode pipeline | Strong | Pipeline graphs cover GQA, MLA, shared Vec aliases, nUpdate, and FD merge. |
| 6. UB / L1 / L0 buffer usage | Strong | Deep annotations and common supplements cover GM, UB, L1, L0A/B/C usage. |
| 7. L1 residency and partitioning | Strong | Q/V L1 snapshot reuse, KP ping-pong, memory lifetime, and L1 partitions are modeled. |
| 8. Sparse window / causal / band / prefix / mask rules | Strong | Sparse policy, host mask packing, invalid-row rules, FD pre/next rebuild, and tests are covered. |
| 9. Online softmax / LSE state | Strong | Shared Vec softmax, MLA nUpdate/aMlaSum, LSE export, and FD stable merge are covered. |
| 10. Workspace layout and offset uniqueness | Strong | Normal ring, FD accum/LSE regions, MLA budget stubs, and scalar offset contracts are covered. |
| 11. Tail handling and alignment | Strong | headDimAlign, 32B Vec alignment, FD GS1 tails, and output padding strip rules are represented. |
| 12. Event/wait/flag synchronization | Strong | RunInfo, shared Vec sync, MLA nUpdate barrier, GQA V_EVENT, FD buffer events, and common hard events are represented and source-backed. |
| 13. Scalar computation, offset computation, div/mod/hoist | Strong | FD prefix sums, MLA ring offsets, atomic bases, and headDimAlign stride are structured. |
| 14. Split-KV partial output/max/sum/LSE merge | Strong | FD metadata, partial accumOut, lseSum/lseMax, stable weights, and final copy-out are modeled. |
| 15. Knobs, hard constraints, forbidden transforms | Strong with minor gaps | 7 knobs, 25 constraints, 23 risks, and forbidden transforms exist; one constraint lacks source-evidence IDs. |

## Source Spot Checks

Judgement labels:

- `verified_against_source`: exact source snippets were inspected and matched the artifact claim.
- `supported_by_artifacts_only`: internally consistent but not fully source-verified in this review.
- `not_verifiable`: source unavailable or insufficient.
- `contradicted_or_suspicious`: source disagreed or claim is likely wrong.

Verified examples:

| Fact | Evidence | Judgement |
|---|---|---|
| Normal workspace binds mm1, vec1, mm2, vec2, then optional FD accum/LSE regions. | `op_kernel/fia_kernel_nonquant_sink.h:373-409` | verified_against_source |
| Nonquant/GQA RunInfo ring maps current slot to MM1, older slot to Vec1/MM2, previous slot to Vec2 before invalidation. | `op_kernel/fia_kernel_nonquant_sink.h:881-909` | verified_against_source |
| MLA RunInfo uses the same three-slot overlap pattern. | `op_kernel/fia_kernel_nonquant_mla_sink.h:834-862` | verified_against_source |
| GQA MM1 Q L1 snapshot is keyed by batch/head/gS1 and reuses cached Q when `canFullLoadQ` holds. | `op_kernel/fia_block_cube_nonquant_gqa_sink.h:988-1050` | verified_against_source |
| GQA MM2 V L1 release is guarded by `!canFullLoadV || mL1.IsTailOf(m)`. | `op_kernel/fia_block_cube_nonquant_gqa_sink.h:1140-1222` | verified_against_source |
| MLA nUpdate compute follows ordered n/cof/eps/clamp/scale steps and writes an int32 vector to `outputBuff2`. | `op_kernel/fia_block_vec_nonquant_mla_sink.h:470-561` | verified_against_source |
| MLA nUpdate apply skips first S-inner loop, broadcasts 128-lane int32 groups, and atomically adds into `mm2ResInt32Gm`. | `op_kernel/fia_block_vec_nonquant_mla_sink.h:657-717` | verified_against_source |
| MLA MM2 waits `syncV1NupdateC2` before the first fixpipe. | `op_kernel/fia_block_cube_nonquant_mla_sink.h:1034-1057` | verified_against_source |
| FD stable merge reads lseSum/lseMax, computes colmax/sub/exp/mul/sum/div weights, then reduces partial outputs. | `op_kernel/fia_block_vec_flashdecode_sink.h:241-290`, `433-556` | verified_against_source |
| Host SetSplitOutput copies fdRes arrays into tilingData fdParams with `usedCoreNum * 2` GS1 end arrays. | `op_host/fia_tiling_nonquant_sink.cpp:326-360` | verified_against_source |
| Common split-core cost is `6*ceil(M/16)+10*ceil(S2/64)` and RecordFDInfo records split-KV metadata. | `common/op_host/split_core.cpp:86-102`, `578-620` | verified_against_source |
| Common buffer/matmul helpers define hard-event pairs, cross-core IDs, and unitFlag constants 0/2/3. | `common/op_kernel/buffer.h:1-180`, `common/op_kernel/matmul.h:1-140` | verified_against_source |
| Common memory-copy, shape/layout, and vector helpers expose int4 divisor, stride limit, axis map/NZ packing, repeat threshold, and invalid-row helpers. | common helper headers | verified_against_source |

No high-value inspected claim was contradicted by source.

## Residual Risk

No blocking Stage-2 issue remains. Minor follow-ups remain for `C-TEMPLATE-IDENTITY` source evidence links, shape/layout forbidden-transform links, and index-only helper functions that should not be treated as full behavioral specs.

## Stage-2 Input Recommendations

Consume directly:

- `cards/optimization_cards.yaml` (all 33 cards now have resolvable source evidence)
- `constraints/constraints.yaml`
- `constraints/forbidden_transforms.yaml`
- `risks/risks.yaml`
- `knobs/tunable_knobs.yaml`
- `auxiliary/workspace_layout.yaml`
- `auxiliary/dataflow_graphs.yaml`
- `auxiliary/pipeline_graphs.yaml`
- `auxiliary/memory_lifetime.yaml`
- `dsl/*_contract.yaml`
- `common_supplement/*`

Consume with awareness of minor follow-ups:

- `C-TEMPLATE-IDENTITY` (currently lacks `source_evidence_ids`).
- `R-SHAPE-LAYOUT-CONTRACT-DRIFT` and `R-COMMON-SHAPE-LAYOUT-VALIDATION-OMITTED` (no related forbidden transforms yet).

Do not consume blindly:

- Index-only function annotations as full behavioral specs.
- Duplicate FD metadata cards as independent schema modules.

## High-Quality Cards

- `OC-FD-STABLE-MERGE`: strong formula, metadata preconditions, LSE risks, and Stage-2 fields.
- `OC-WORKSPACE-NORMAL-RING`: directly links host sizing and kernel SetGlobalBuffer order.
- `OC-MLA-NUPDATE-SIDECHANNEL`: captures numeric compute, broadcast group, atomic target, and risks.
- `OC-GQA-MM1-Q-L1-SNAPSHOT-REUSE`: source-backed L1 residency, sparse guards, and lowering hint.
- `OC-FD-METADATA-BRIDGE`: good host-to-kernel metadata bridge structure.
