# Stage 4 implementation audit — 2026-09-03

Verdict: the pipeline is implemented and statically validated, but execution is correctly blocked
until Stage 2/3 complete and Stage 3 passes all renderer-ingestion authorization requirements.

## Authorization and claim scope

- The gate reads exact Stage 3 dataset/report hashes and requires held-out renderer-ingestion
  decodability on the supported omitted/blurred subset, set-2 transfer, renderer-ingestion
  direction alignment, and complete data. Pooled plans containing explicit policy text cannot
  authorize intervention.
- Planner-boundary results cannot authorize intervention.
- Recipient source/target selection is behavior-blinded and bound back to every immutable Stage 3
  candidate row; editing candidate text inside the audit invalidates it.
- All recipients and explicit sources are paraphrase set 2.
- The result schema fixes `heldout_task_case_study` and `cross_task_generalization_claim=false`.
- Cross-family language is policy orientation; only report-to-archive symlink transfer is
  fact-specific.

## Intervention integrity

- The primary edit is a single-position causal subspace intervention, not complete-activation
  replacement. The manifest freezes the exact module/layer, post-block location, `END_PLAN` token
  index, prompt-prefill phase, and downstream-layer count.
- Runtime requires an exact module/index match, at least one downstream layer, exactly one edit,
  and bit-identical next-token logits for strength-zero hooked versus unhooked forwards.
- Its update changes only the selected unit direction; projection before/after, L2 norm, edit count,
  and maximum orthogonal residual are persisted. A primary orthogonal residual over `1e-5` aborts.
- The planner adapter is disabled during every renderer capture, logit calculation, teacher-forced
  pass, and generation.
- The random vector is deterministically projected orthogonal to the target and validated by dot
  product. Stage 3 auxiliary controls use layer-qualified paths.
- The unrelated-fact null is a paired authentication-session capture on the development recipient.
- Only random orthogonal, unrelated authentication, paraphrase identity, and lexical framing are
  matched null controls. Development scalar values and the early layer are diagnostics; the held-out
  A/B vector is a positive oracle. None can affect selection or the transfer-success calculation.
- Direction materialization binds every vector, centroid/value source, model, adapter, and activation
  to the experiment manifest by SHA-256.

## Analysis integrity

- Full code sampling cannot be prepared until the development-only distribution check passes.
- The check requires exactly the target and four development-only matched null controls at every
  frozen strength; the held-out oracle is forbidden. Raw logits, divergence specification, prompt,
  direction set, and result files are
  hash-bound.
- It records patched/unpatched KL, A/B Jensen-Shannon divergence, relevant-token logit changes, and
  teacher-forced A-vs-B continuation log-odds at the preregistered first divergence.
- The report measures bidirectionality as opposite movement of one A-minus-B executable-behavior
  contrast, not as two unrelated rate increases.
- Causal success additionally requires the weaker target direction to beat all four matched nulls,
  set-2 inputs, and each target to lose at most one functional output versus unpatched.
- All 17 conditions share the same 16 seeds by sample index; the manifest rejects a mismatch.
- Functional code passing both mutually exclusive suites yields `invalid_task_or_tests`.
- Malformed/length outputs remain model failures; missing jobs remain incomplete.

## Conditional branches

The primary run is single-position only. The runbook explicitly blocks recurrent steering unless
the development edit changes distributions but the effect washes out in full generation; any such
result must be labeled activation steering. Contradictory-text runs are blocked until the omitted
recipient finishes. Planner-side intervention is not prioritized unless renderer-side causal
interchange succeeds.

## Verification performed

- Repository-wide Ruff: passed.
- Repository-wide mypy: passed for 29 source files.
- Repository-wide pytest: 91 tests passed.
- `validate-stage2-config`, `validate-stage3-config`, and `validate-stage4-config`: passed.
- Stage 3 correctly reports its paraphrase meaning audit as pending; Stage 4 does not bypass it.

GPU execution was not simulated as evidence. The hook/materialization runtime is reserved for the
pinned local Qwen model on the Windows RTX 5080 PC after its canaries and audits pass.
