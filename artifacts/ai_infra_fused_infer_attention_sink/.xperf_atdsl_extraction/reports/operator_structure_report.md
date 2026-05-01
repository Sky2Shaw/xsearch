# AiInfraFusedInferAttentionSink Stage 1 Structure Report

Generated: 2026-05-01T01:46:30.097086+00:00

## Coverage

- Files scanned: 38
- Functions indexed: 616
- Brief annotations: 18
- Deep annotations: 126

## Critical Coverage

- GQA `FiaBlockCubeNonQuantGqa<FIAT, Config>::ComputeMm2`: covered in deep annotations and critical path.
- MLA `FiaBlockCubeNonQuantMla<FIAT>::ComputeMm2`: covered in deep annotations and critical path.
- MLA `FiaBlockCubeNonQuantMla<FIAT>::ProcessMm2`: covered in deep annotations and critical path.
- MLA nUpdate: covered through `AmlaVecCompute` and `ProcessAmlaNupdate`.
- FlashDecode merge: covered through `FiaBlockVecFlashDecode<FIAT>::FlashDecode` and FD helpers.

## Top DSL Sections

1. `pipeline.stage_graph`
2. `memory.l1_residency`
3. `mla.nupdate`
4. `flash_decode.merge`
5. `workspace.layout`
