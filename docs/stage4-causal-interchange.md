# Stage 4: renderer-ingestion causal interchange on the Windows RTX 5080 PC

Stage 4 tests whether changing the local open-weight renderer's internal policy-orientation value
at one `END_PLAN` position changes executable policy behavior. It cannot be run or interpreted
until Stage 3 authorizes it. Hosted Kimi behavior is not mechanistic evidence for Qwen, and these
results apply only to the pinned local Qwen model and selected adapter/base-renderer pairing.

This is a five-task pilot with one held-out task (`path_symlink_archive`). Its strongest possible
claim is a one-task symlink-policy case study, never cross-task generalization. Across unrelated
families the direction is called a **policy-orientation direction**. The only fact-specific
transfer in this corpus is `path_symlink_report` to `path_symlink_archive`.

## Hard authorization boundary

`prepare-stage4-recipient-audit` and `prepare-stage4-experiment` both verify the exact Stage 3
dataset/report hashes. The experiment is blocked unless all four report fields are true:

- renderer-ingestion policy decodability;
- transfer to paraphrase set 2;
- alignment of renderer-ingestion task-level directions; and
- a complete Stage 3 dataset.

Planner-input or planner-output decoding is localization evidence only and cannot unlock Stage 4.

## Frozen design

The configuration is [config/stage4.toml](../config/stage4.toml). Before any Stage 4 result it
freezes the dev/test tasks, early layer, development distribution thresholds, 16 samples per
condition, three Stage 3 strength multipliers, and task-specific first-divergence continuations in
[data/stage4/divergence-spec.json](../data/stage4/divergence-spec.json).

The primary recipient audit is behavior-blinded: the reviewer sees task inputs and plan text, not
generated code or test outcomes. For dev and test it selects:

1. a full, explicit-A, paraphrase-set-2 source;
2. a full, explicit-B, paraphrase-set-2 source; and
3. one naturally generated concise/minimal set-2 plan labeled omitted or blurred.

The reviewer confirms the omitted plan remains meaningful and neutral, uses the same surface
request, and is matched on format, length, and non-target details where possible. No fields are
deleted to manufacture an omission.

```powershell
uv run sable-ir prepare-stage4-recipient-audit
# Fill selections and every review flag; add reviewer and completed_at.
uv run sable-ir prepare-stage4-experiment --run-id interchange-01
```

The experiment manifest hash-binds Stage 2/3 configurations, dataset, activation manifest,
selection, held-out results, report, recipient audit, model revision, adapter files, sandbox,
directions, centroids, prompts, and strengths. It refuses overwrite.

## Direction materialization and matched controls

Run on the PC after the recipient audit:

```powershell
uv run sable-ir materialize-stage4-directions `
  artifacts\stage4\experiments\interchange-01\manifest.json `
  --output artifacts\stage4\experiments\interchange-01\direction-set.json
```

The primary direction and scalar A/B centroids come only from training tasks and paraphrase set 1.
Every probe was fit on all training activation rows with equal total base-task weight; task-level
A/B means are used only to estimate and align directions. Materialization supplies all eight
target/control artifacts:

- primary policy orientation;
- seeded random direction explicitly projected orthogonal to the target;
- an unrelated authentication-session fact from a paired renderer-ingestion capture;
- paraphrase-set identity at the same layer;
- a set-1 lexical-framing direction evaluated on the opposite framing;
- target-direction scalar values from the unrelated development task;
- the preregistered early-layer training direction; and
- the full held-out explicit-B minus explicit-A activation vector.

Layer-qualified hashes prevent a control estimated at one layer from being used at another.
Direction vectors are normalized. Non-value controls receive the exact target edit norm for that
recipient/policy; centroid/value controls report their realized norm. The planner adapter remains
loaded only for provenance and is disabled for every renderer capture and generation.

## Cheap development check

Before sampling complete held-out code:

```powershell
uv run sable-ir run-stage4-sanity `
  artifacts\stage4\experiments\interchange-01\manifest.json `
  artifacts\stage4\experiments\interchange-01\direction-set.json `
  --output-directory artifacts\stage4\experiments\interchange-01\sanity

$selectArgs = @(
  "select-stage4-sanity",
  "artifacts\stage4\experiments\interchange-01\manifest.json"
)
Get-ChildItem artifacts\stage4\experiments\interchange-01\sanity\*result.json |
  ForEach-Object { $selectArgs += @("--result", $_.FullName) }
$selectArgs += @(
  "--output",
  "artifacts\stage4\experiments\interchange-01\sanity-selection.json"
)
uv run sable-ir @selectArgs
```

For the primary, random-orthogonal, and lexical controls at every preregistered strength, the
runtime preserves full raw logits by hash and reports patched-vs-unpatched KL, A-vs-B Jensen-Shannon
divergence, relevant-token logit changes, and teacher-forced A/B log-odds at the frozen first code
divergence. Selection uses the development task only. Full code is blocked unless the target clears
both configured floors and exceeds both controls. Failure means the edit is weak or misplaced, not
that the represented policy has no causal role.

## Primary single-position run

```powershell
uv run sable-ir prepare-stage4-full-run `
  artifacts\stage4\experiments\interchange-01\manifest.json `
  artifacts\stage4\experiments\interchange-01\sanity-selection.json `
  artifacts\stage4\experiments\interchange-01\direction-set.json `
  --run-id heldout-01 --run-directory artifacts\stage4\full\heldout-01

uv run sable-ir run-stage4-full artifacts\stage4\full\heldout-01\manifest.json
uv run sable-ir evaluate-stage4-full artifacts\stage4\full\heldout-01\manifest.json
uv run sable-ir report-stage4 artifacts\stage4\full\heldout-01\manifest.json `
  --output artifacts\stage4\full\heldout-01\report.json
```

The primary hook edits exactly one residual-stream position: renderer `END_PLAN`. For the target
direction it applies `h' = h + strength * (c_v - w'h)w`. The frozen full-run matrix contains one
unpatched condition plus A/B injections for all eight target/control directions, with 16 samples
each (272 jobs). Each record includes the prompt and direction hashes, exact seed, raw output,
candidate hash, projection before/after, edit norm, edit count, and maximum orthogonal change.
The target edit aborts if it is not applied exactly once.

The report uses the A-minus-B executable-behavior contrast, so “bidirectional” means A injection
moves that contrast toward A and B injection moves the same contrast toward B. Causal success also
requires the weaker target shift to exceed every matched control, set-2 inputs, and target
functionality no more than five percentage points below unpatched. A functional output passing both
mutually exclusive suites produces `invalid_task_or_tests` immediately. With one held-out task,
even a passing report remains `heldout_task_case_study` and `cross_task_generalization_claim=false`.

## Optional branches and stopping rules

The primary run is always single-position. Recurrent steering is authorized only when the cheap
distribution check changes but the full-generation effect washes out; it must be labeled
`activation steering` and reported separately. Contradictory-text intervention is allowed only
after the omitted-plan result. Planner-side intervention is cut unless renderer interchange first
succeeds. These branches are deliberately not part of the primary CLI, preventing an accidental
scope expansion before its prerequisite is documented.

## Audit trail

Use a new run ID for every rerun. Never edit a completed JSON artifact. The Stage 4 chain is:

```text
Stage 3 dataset + selection + heldout + report
  -> behavior-blinded recipient audit
  -> experiment manifest
  -> materialized direction set
  -> raw sanity distributions + result records
  -> dev-only sanity selection
  -> immutable full-run manifest
  -> raw generations + candidates + sandbox evaluations
  -> Stage 4 report
```

Every arrow is checked by SHA-256. GPU/CUDA sampling seeds support auditing but are not claimed to
be bit-exact across drivers. Do not report a Stage 4 number while any preceding hash check, audit,
generation, or evaluation is incomplete.
