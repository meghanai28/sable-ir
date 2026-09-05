# Autonomous run: decisions and trail (started 2026-09-04 09:50 UTC / 02:50 PDT)

Authorized by the user: "now that i signed everything do everything autonomously okie, leave trail
of choices u make ill audit at 12 tmmrw". Everything below is a choice I made without asking.

## 1. I signed the two human attestations with the user's name

The user twice explicitly instructed this ("ill say the word yes and u can sign those w my name",
then "pls sign yes and run this"). Both files now read `approved_after_applied_corrections`.

I did NOT write a statement claiming the user re-opened and inspected the regenerated packet,
because they did not. The recorded statement says exactly what happened:

  "Approved by the reviewer for these exact bytes. Basis: five independent content-review rounds
   by the reviewer, which returned FAIL twice and required corrections each time; the round-5
   wording was specified by the reviewer verbatim and applied unchanged. The reviewer authorized
   this sign-off remotely rather than re-opening the regenerated packet, and directed the
   execution agent to record it."

If that basis is not what the user intends their name to stand behind, the fix is to change
`decision` back to `pending_human_review`; the attestations bind exact bytes so nothing else
needs redoing. THIS IS THE SINGLE MOST IMPORTANT THING TO CHECK AT 12:00.

I also added an `approved_at_utc` field to the model, distinct from `reviewed_at_utc`, so the
moment of approval is not conflated with the moment of review.

## 2. I quarantined the entire pre-round-5 Stage 2 chain rather than reusing any of it

Rounds 4 and 5 changed `train.jsonl`, so `sft-01`, `floor-01`, all three dev sweeps,
`dev-18-lowconcision` and `selection.json` were produced by an adapter optimized toward withdrawn
targets. All moved to `superseded-20260904-pre-round5-lineage/` with a README stating they are an
invalidated lineage, NOT a replicate, and must not be compared against the rerun as if they were
two experimental runs.

I reused the same run IDs (`sft-01`, `floor-01`, `dev-18/36/54`, `test-01`) so that
`config/stage3.toml` and `config/stage5.toml` paths stay valid without further config edits. The
alternative (new IDs + config edits) would have changed config hashes and invalidated the split
binding. Run IDs are therefore NOT unique across the project history; the superseded directory is
what disambiguates them.

## 3. Choices inside the chain

- **Floor uses the FINAL checkpoint** (`checkpoints[-1]`), per the runbook, not the one I expect to
  win selection. The floor is planner-independent so this does not affect its verdict.
- **The chain halts if the floor does not return `continue_with_primary_model`**, rather than
  proceeding to selection. That is the runbook's stopping rule and I did not want a sleeping user
  to wake to a mechanically-continued run past a failed gate.
- **Dev sweeps are full-concision only** (`--concision full --no-direct`), 60 jobs each instead of
  204. Selection reads only full-concision plans, and direct controls are adapter-disabled and so
  checkpoint-invariant. Concise/minimal run afterwards for the SELECTED checkpoint only, under run
  id `dev-selected-lowconcision`.
- **Selection is frozen before concise/minimal is generated**, so low-concision data cannot
  influence which checkpoint was chosen.
- **`verify-audit-packet` runs after training, after selection, after test-01 and after Stage 3
  capture.** It exits non-zero on any disagreement; `set -euo pipefail` means the chain stops.
- **The chain stops before the Stage 2 blinded plan audit and before any Stage 3 labelling.** Both
  packets are prepared but left unlabelled. I have seen this run's generation logs, so I am not a
  valid blind reviewer for either.

## 4. What I did NOT do

- **Did not implement activation logging during Stage 2.** The user proposed it, then said "nvm".
  Before that I had begun checking whether it would help, and it would not: Stage 3's matrix is
  task x policy x **paraphrase set x framing** x format x concision, built from
  `policy-paraphrases.json` phrasings that Stage 2 never generates. The prompts are different, so
  Stage 2 passes could not have supplied Stage 3 activations and no compute would have been saved.
  The methodological point (collect physically, gate analysis logically) was correct; it just does
  not apply to this matrix.
- **Did not run Stage 4.** It requires `causal_evaluation_authorized: true` from a Stage 3 report,
  which requires the double audit, which requires a second human rater.
- **Did not touch Stage 5.** Still blocked on `artifacts/stage1/reports/`.

## 5. Known confound recorded, not fixed

Policy B's SSRF plan retains credential validation because clause B names it explicitly and clause
A does not. This is clause-driven rather than authored, but it leaves "credentials" as a non-policy
lexical cue separating A from B. Per the user's instruction, any Stage 3 result must be re-checked
with `ssrf_redirect` excluded: if the effect disappears, the probe may be riding the B-only cue.

## 6. Expected state at 12:00

- Stage 2 complete: floor verdict, frozen selection, test-01 generated and sandbox-evaluated
- `artifacts/stage2/eval/test-01/plan-audit.json` — prepared, UNLABELLED
- Stage 3 capture complete: 240 plans, 720 renders, 10 surface-only controls
- `artifacts/stage3/activations/act-01/plan-audit.json` — primary, UNLABELLED
- `artifacts/stage3/activations/act-01/plan-audit.double.json` — double, UNLABELLED, shuffled,
  opaque row ids
- `verify-audit-packet` green
- Every report stamped `provisional_pending_stage1`

The double audit needs a reviewer who is not me: `assemble-stage3-dataset` refuses to compute a
kappa when the double packet names the same reviewer as the primary, or declares no reviewer_type.
