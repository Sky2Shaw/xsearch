# AiInfraFusedInferAttentionSink Stage 1 Structure Report

Generated: 2026-05-01T01:46:30.097086+00:00

## Coverage

- Files scanned: 38
- Functions indexed: 616
- Brief annotations: 18
- Deep annotations: 128

## Critical Coverage

- GQA `FiaBlockCubeNonQuantGqa<FIAT, Config>::ComputeMm2`: covered in deep annotations and critical path.
- MLA `FiaBlockCubeNonQuantMla<FIAT>::ComputeMm2`: covered in deep annotations and critical path.
- MLA `FiaBlockCubeNonQuantMla<FIAT>::ProcessMm2`: covered in deep annotations and critical path.
- MLA nUpdate: covered through `AmlaVecCompute` and `ProcessAmlaNupdate`.
- FlashDecode merge: covered through `FiaBlockVecFlashDecode<FIAT>::FlashDecode` and FD helpers.

## Top DSL Sections

1. `pipeline.stage_graph`
2. `mla.nupdate`
3. `flash_decode.metadata_bridge`
4. `shape_layout.contract`
5. `sparse.policy`
