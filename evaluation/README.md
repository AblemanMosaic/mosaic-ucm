# Track C study execution

1. Run `python tools/finalize_architecture_study.py` after intentionally changing
   any task, context, rubric, or oversight material.
2. Fill and root `EXECUTION-CONTEXT.template.json` with the actual model, settings, environment, and shared toolchain.
3. Run `python tools/build_architecture_study_kits.py --execution-context <registration.json> --output <directory>`.
3. Assign each sealed run kit independently. Keep model settings and human oversight
   identical across arms as required by the protocol.
4. Preserve prompt, context, actions, diff, tests, review, repairs, journal, receipts,
   elapsed times, and the completed rooted result.
5. Validate every result with `ucm study-validate-result`.
6. Aggregate only after the full registered denominator is present with
   `ucm study-aggregate`.

The builder performs no model execution. The pilot authorizes no effects, software
adoption, publication claim, or authority change. Its purpose is to make a future
comparison reproducible and auditable.
