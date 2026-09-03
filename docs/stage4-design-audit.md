# Stage 4 implementation audit — 2026-09-03

Verdict: the pipeline is implemented and statically validated, but execution is correctly blocked
until Stage 2/3 complete and Stage 3 passes all renderer-ingestion authorization requirements.

## Authorization and claim scope

- The gate reads exact Stage 3 dataset/report hashes and requires renderer-ingestion decodability,
  set-2 transfer, renderer-ingestion direction alignment, and complete data.
- Planner-boundary results cannot authorize intervention.
- Recipient source/target selection is behavior-blinded and bound back to every immutable Stage 3
  candidate row; editing candidate text inside the audit invalidates it.
- All recipients and explicit sources are paraphrase set 2.
- The result schema fixes `heldout_task_case_study` and `cross_task_generalization_claim=false`.
- Cross-family language is policy orientation; only report-to-archive symlink transfer is
  fact-specific.

## Intervention integrity

- The primary edit is registered on the selected decoder block and is applied exactly once at the
  renderer `END_PLAN` token.
- Its update changes only the selected unit direction; projection before/after, L2 norm, edit count,
  and maximum orthogonal residual are persisted. A primary orthogonal residual over `1e-5` aborts.
- The planner adapter is disabled during every renderer capture, logit calculation, teacher-forced
  pass, and generation.
- The random vector is deterministically projected orthogonal to the target and validated by dot
  product. Stage 3 auxiliary controls use layer-qualified paths.
- The unrelated-fact control is an actual paired authentication-session capture, not a relabeled
  plan-format vector. The full-vector control is the held-out explicit B-minus-A source state.
- Direction materialization binds every vector, centroid/value source, model, adapter, and activation
  to the experiment manifest by SHA-256.

## Analysis integrity

- Full code sampling cannot be prepared until the development-only distribution check passes.
- The check requires exactly target, random-orthogonal, and lexical-framing A/B pairs at all frozen
  strengths. Raw logits, divergence specification, prompt, direction set, and result files are
  hash-bound.
- It records patched/unpatched KL, A/B Jensen-Shannon divergence, relevant-token logit changes, and
  teacher-forced A-vs-B continuation log-odds at the preregistered first divergence.
- The report measures bidirectionality as opposite movement of one A-minus-B executable-behavior
  contrast, not as two unrelated rate increases.
- Causal success additionally requires the weaker target direction to beat every control, set-2
  inputs, and functionality within five points of unpatched.
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
- Repository-wide mypy: passed for 26 source files.
- Repository-wide pytest: 85 tests passed.
- `validate-stage2-config`, `validate-stage3-config`, and `validate-stage4-config`: passed.
- Stage 3 correctly reports its paraphrase meaning audit as pending; Stage 4 does not bypass it.

GPU execution was not simulated as evidence. The hook/materialization runtime is reserved for the
pinned local Qwen model on the Windows RTX 5080 PC after its canaries and audits pass.
