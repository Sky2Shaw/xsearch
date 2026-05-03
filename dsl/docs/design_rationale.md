# Stage2 DSL Deep Optimization Rationale

The previous Stage2 DSL already captured important optimization structures: RunInfo ring pipeline, GQA L1 V reuse, FlashDecode metadata bridge, stable LSE merge, workspace ABI, sparse policy, and MLA tail binding policy. However, it remained a mostly flat schema. That is risky for an optimization agent because flat fields do not clearly distinguish:

- semantic invariants vs. performance schedules;
- hardware limits vs. implementation choices;
- candidate actions vs. fixed/forbidden contracts;
- semantic DSL fields vs. concrete AscendC variable names;
- one-time deltas vs. replayable transform traces.

The optimized design follows seven rules.

1. **Separate semantic correctness from performance schedule.** `semantic_ir` owns op meaning, shape/layout, numerical contracts, and profile identity.
2. **Make schedulable kernel structure explicit.** `kernel_ir` owns loop nest, tiles, pipeline, memory plan, workspace, sparse policy, flash-decode, MLA, and scalar offset rules.
3. **Make Ascend hardware a contract.** `hardware_contract_ir` owns memory spaces, engines, alignment, events, and intrinsic constraints used by validators.
4. **Promote search knobs into schedule points.** Agents should mutate `schedule_points`, not arbitrary YAML fields.
5. **Use transform traces, not blind field diffs.** Each change carries intent, preconditions, expected effects, risks, validators, and mutations.
6. **Use semantic binding before lowering.** Lowering uses `semantic_id -> reviewed binding`, not literal variable names such as `s2BaseSize`.
7. **Record every candidate execution.** `execution_ir` stores validation, lowering, compile, correctness, benchmark, profile counters, and failure classification.

The result is not a new AscendC replacement language. It is an agent-facing compiler protocol for attention-class kernel optimization.
