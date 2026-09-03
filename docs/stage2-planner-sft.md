# Stage 2: planner QLoRA SFT on the Windows RTX 5080 PC

Stage 2 trains a LoRA adapter so a local planner emits information-complete plans that transfer the
assigned A/B policy to a frozen renderer, then measures the post-SFT length/format frontiers,
the model-floor rule, and the bottleneck sanity check from the proposal. Everything below runs on the
Windows PC with the RTX 5080 (16 GiB). This track reads and hash-binds the Stage 1 report for its
continuation status but never mutates Stage 1 artifacts or code.

## What is already frozen in the repository

| Artifact | Path | Role |
| --- | --- | --- |
| Config | `config/stage2.toml` | Pinned Qwen3.5-4B / 9B revisions, 16 GiB QLoRA budget, sandbox `linux/amd64`, pilot split |
| Authored plans | `data/stage2/reference-plans.json` | 20 hand-written SFT targets (5 tasks x A/B x structured/freeform) plus surface and policy-wording paraphrases |
| Split | `data/stage2/split.json` | Base-task split with exact task hashes: train 3 / dev 1 / test 1 |
| Corpus | `data/stage2/reference-corpus.json` | 240 rows = plans expanded over 2 surfaces x 3 clause orders x 2 wordings |
| Audit template | `data/stage2/reference-audit.json` | Behavior-blinded audit, all flags false until reviewed |
| Decisions | `data/stage2/reference-audit.decisions.json` | 20 plan decisions + 15 paraphrase decisions; expands into the 240-row audit |
| Model canary | `artifacts/stage2/canary/<model>--<revision>.json` | NF4 load, one full-length training step, generation; required by preflight |

`design_mode = "pilot"` runs the complete Stage 2 track on the five audited tasks. Every report is
labeled `pilot: true`. The 12/6/6 design (`design_mode = "full"`) becomes available once 24 audited
base tasks exist; the config validator refuses any other counts in full mode.

The model is `Qwen3_5ForConditionalGeneration` (natively multimodal). It is loaded through
`AutoModelForMultimodalLM` in NF4, and LoRA is restricted by regex to language-model linear modules:
full-attention q/k/v/o, Gated DeltaNet `in_proj_qkv`/`in_proj_z`/`out_proj`, and MLP projections
(200 modules on the 4B). The vision tower, embeddings, norms, conv1d, and gate projections are never
trainable; the trainer aborts if any trainable parameter is outside `language_model` or is not a
LoRA weight. Thinking is disabled for both roles; the renderer is the same NF4 base with the adapter
disabled.

## PC setup (PowerShell)

1. Install Docker Desktop (WSL2 backend), Git for Windows, Python 3.11+, and `uv`. The NVIDIA
   driver must be recent enough for CUDA 12.8 (Blackwell needs R570+).
2. Clone fresh so `.gitattributes` gives LF line endings (hash bindings depend on exact bytes):

   ```powershell
   git clone <repo-url> C:\sable-ir
   cd C:\sable-ir
   uv sync --extra dev --extra stage2
   ```

   The `stage2` extra resolves `torch==2.9.1+cu128` from the PyTorch CUDA 12.8 index on Windows,
   plus `transformers`, `peft`, `accelerate`, and `bitsandbytes` (Windows wheels). Optional
   `flash-linear-attention`/`causal-conv1d` kernels are Linux/Triton-only; without them the
   Gated DeltaNet layers use the slower PyTorch fallback, which is recorded as informational.
3. Keep the checkout near the drive root; job directories are deep and Windows limits paths to
   260 characters unless long paths are enabled.
4. Verify the CUDA build and the sandbox before spending GPU time:

   ```powershell
   uv run python -c "import torch; print(torch.cuda.get_device_name(0), torch.version.cuda)"
   uv run sable-ir stage2-sandbox-smoke --output artifacts\stage2\sandbox-smoke.json
   ```

   The smoke run pulls the pinned `linux/amd64` Python image and confirms both reference
   implementations of every task reproduce the A/B matrix through Docker Desktop.
5. Run the model canary for the active model (a few minutes of GPU time):

   ```powershell
   uv run sable-ir stage2-model-canary
   ```

   It loads the pinned model in NF4 through the official multimodal auto class, attaches the
   language-model-only LoRA, runs one masked optimizer step on a row padded to the full 2048-token
   budget, generates with the adapter enabled and inside `disable_adapter()`, and records peak GPU
   memory and package versions to `artifacts/stage2/canary/`. A failed attempt is recorded too.
   Preflight requires a passed canary for the active model with the currently installed packages.
   The 4B run is expected to fit within 16 GiB; the 9B fallback remains conditional on passing
   this canary. This is an implementation check, not an experiment.

## Data track (no GPU)

The split, corpus, and audit template are already generated. Provenance of the authored plans: I
authored the plans from the surface request and visible safety document, then checked them against
the reference implementations and tests for behavioral consistency. Every plan detail must be
inferable from the model's input; the audit rejects information obtainable only from reference
code or hidden tests.

Remaining human step: the behavior-blinded reference audit. Edit
`data/stage2/reference-audit.decisions.json`:

- `decisions`: for each of the 20 (task, policy, format) plans set the eight flags honestly,
  including `inferable_from_visible_inputs_only`, and add `notes` where useful.
- `paraphrases`: for each of the 15 authored input paraphrases (5 surface requests, 10
  policy-wording clauses) set `preserves_meaning` only if the paraphrase carries exactly the
  original request or policy meaning. Reviewing the 20 output plans alone does not verify this.
- Set `reviewer` and `completed_at` (ISO 8601).

Then expand and freeze:

```powershell
uv run sable-ir complete-stage2-reference-audit
uv run sable-ir validate-stage2-reference-audit
uv run sable-ir freeze-stage2-dataset --destination artifacts\stage2\dataset
```

The freeze refuses to run unless every row has a passed, exact-hash audit, every paraphrase passed
meaning review, the audit is bound to the current corpus, split, and authored-plans file, no base
task appears in two splits, and no task file changed since the split was frozen. Output:
`train.jsonl` (144 rows), `dev.jsonl` (48), `test.jsonl` (48) and a manifest with all hashes.

If a plan fails review, edit `data/stage2/reference-plans.json`, delete
`reference-corpus.json`, `reference-audit.json`, and the decisions file, and rerun
`build-stage2-reference-corpus` and `prepare-stage2-reference-audit`. The split stays frozen.

## Training

```powershell
uv run sable-ir stage2-preflight --output artifacts\stage2\preflight.json
uv run sable-ir prepare-stage2-training --dataset-manifest artifacts\stage2\dataset\manifest.json --run-id sft-01
uv run sable-ir train-stage2 artifacts\stage2\training\sft-01\manifest.json --confirm sft-01
```

Preflight records: frozen split, complete audit, the Stage 1 `continue_to_stage2` gate, a passed
model canary for the active model, an RTX 5080 with >= 15 GiB, installed package versions, Windows,
and the Docker sandbox. Training refuses to start unless every check passed.

Stage 1 override: if the Stage 1 report is not yet available at `stage1_report_path`, pass
`--stage1-gate-override "<reason>"` to `prepare-stage2-training` to start computation early; the
reason and the gate status at authorization are recorded verbatim in the training manifest and
the preflight. Every Stage 2 report re-reads the Stage 1 report when it is built and carries
`stage1_gate` and `stage2_status`:

- Stage 1 later passes: `valid_continuation`; Stage 2 stands as a continuation.
- Stage 1 still missing: `provisional_pending_stage1`; do not treat any number as final.
- Stage 1 fails: `exploratory_stage1_failed`; Stage 2 is exploratory and cannot receive
  `continue_to_stage2` standing. Rebuild reports (new output paths) once Stage 1 finishes.

Budget on the 16 GiB card: NF4 4B weights ~2.6 GiB, rank-32 adapters + optimizer states < 1 GiB,
activations at 2048 tokens with gradient checkpointing and micro-batch 1 x 8 accumulation
~3-5 GiB. The 4B run is expected to peak at 8-10 GiB; the canary measures the worst-case step and
the result records `peak_gpu_memory_gib`. The frozen rows are
about 700-1000 tokens each; the trainer aborts rather than truncate. Three epochs over 144 rows
is 54 optimizer steps; expect well under an hour. Per-epoch checkpoints land in
`artifacts/stage2/training/sft-01/checkpoints/checkpoint-<step>/` with adapter hashes recorded in
`training-result.json`. The trainer never reads `test.jsonl`.

If preflight shows an unexpected GPU name, stop: the run is only authorized on the RTX 5080.

## Model-floor run (II.B.6)

Before selecting a checkpoint, check that Qwen3.5-4B is capable enough with all five tasks:

```powershell
uv run sable-ir prepare-stage2-eval --run-id floor-01 --kind model_floor `
  --adapter artifacts\stage2\training\sft-01\checkpoints\checkpoint-54 `
  --training-result artifacts\stage2\training\sft-01\training-result.json
uv run sable-ir run-stage2-eval artifacts\stage2\eval\floor-01\manifest.json
uv run sable-ir evaluate-stage2-eval artifacts\stage2\eval\floor-01\manifest.json
uv run sable-ir report-stage2-eval artifacts\stage2\eval\floor-01\manifest.json --output artifacts\stage2\eval\floor-01\report.json
```

A model-floor run is 180 plans, 720 renders, and 120 direct completions (original benchmark,
surface-only, relevant-clause A/B, full-document A/B). Generation is resumable: rerun the same
command after an interruption and completed jobs are skipped; `--phase plans|renders|direct` and
`--limit N` allow staged execution. Renders and direct completions run the frozen base model:
the renderer generates inside PEFT's `with model.disable_adapter():` block, so the adapter never
touches code generation. All sampling uses the preregistered settings in `[generation]` (based on
Qwen's recommended non-thinking configuration) with per-job fixed and recorded seeds; CUDA
sampling is not bit-reproducible across package, driver, or hardware changes, so the seeds
support auditing rather than exact replay.

The report's `model_floor` block compares full-document direct and full structured-plan
assigned-policy-and-functional rates to the 0.30 threshold. Both must pass to continue, but the
failing condition determines the response:

- Full-document direct below 0.30: `move_to_fallback_model`. The base model cannot do the tasks
  even with the complete document. Run `stage2-model-canary` for the 9B, and only if it passes set
  `[model] active = "fallback"` in `config/stage2.toml` (Qwen3.5-9B, ~6 GiB NF4; keep 2048
  tokens) and redo the data freeze, preflight, and training with a new run ID.
- Direct passes but full structured plan below 0.30: `stop_or_pivot`. This points at the planner
  or the bottleneck, not automatically at model size; do not switch models on this verdict.
- Both pass: `continue_with_primary_model`.

The `bottleneck_sanity` block flags when the plan bottleneck costs more than 5 points
of functionality or 10 points of assigned-policy pass rate relative to full-document direct.

## Dev-only checkpoint selection

Run one `dev_selection` evaluation per epoch checkpoint (dev split only: `ssrf_redirect`), then
select:

```powershell
foreach ($step in 18, 36, 54) {
  uv run sable-ir prepare-stage2-eval --run-id dev-$step --kind dev_selection `
    --adapter artifacts\stage2\training\sft-01\checkpoints\checkpoint-$step `
    --training-result artifacts\stage2\training\sft-01\training-result.json
  uv run sable-ir run-stage2-eval artifacts\stage2\eval\dev-$step\manifest.json
  uv run sable-ir evaluate-stage2-eval artifacts\stage2\eval\dev-$step\manifest.json
  uv run sable-ir report-stage2-eval artifacts\stage2\eval\dev-$step\manifest.json --output artifacts\stage2\eval\dev-$step\report.json
}
uv run sable-ir select-stage2-checkpoint `
  --report artifacts\stage2\eval\dev-18\report.json `
  --report artifacts\stage2\eval\dev-36\report.json `
  --report artifacts\stage2\eval\dev-54\report.json `
  --training-result artifacts\stage2\training\sft-01\training-result.json `
  --output artifacts\stage2\selection.json
```

The step numbers come from `training-result.json` (`checkpoints[].global_step`). Selection uses the
dev assigned-policy-and-functional rate over full-concision plans, ties broken by the earliest
step; it accepts only complete `dev_selection` reports whose adapter hashes match the training
result.

## Test-split evaluation and audit

```powershell
uv run sable-ir prepare-stage2-eval --run-id test-01 --kind test_final `
  --adapter <selected checkpoint directory> `
  --training-result artifacts\stage2\training\sft-01\training-result.json `
  --checkpoint-selection artifacts\stage2\selection.json
uv run sable-ir run-stage2-eval artifacts\stage2\eval\test-01\manifest.json
uv run sable-ir evaluate-stage2-eval artifacts\stage2\eval\test-01\manifest.json
uv run sable-ir prepare-stage2-plan-audit artifacts\stage2\eval\test-01\manifest.json --output artifacts\stage2\eval\test-01\plan-audit.json
# ...label every row without viewing code or outcomes, set reviewer/completed_at...
uv run sable-ir report-stage2-eval artifacts\stage2\eval\test-01\manifest.json `
  --plan-audit artifacts\stage2\eval\test-01\plan-audit.json `
  --output artifacts\stage2\eval\test-01\report.json
```

`test_final` refuses any adapter other than the dev-selected one. The report gives, per
format x concision cell and per observed plan-length bin: functional rate, assigned-policy pass,
assigned-and-functional, opposite-policy, A-versus-B controllability, plan tokens (exact count of
the visible plan including `END_PLAN`), document-to-plan compression, malformed-plan rate, and with
an audit: visible retention, HU+ per policy against this run's surface-only baseline, false
certificates, and confident-wrong-clause rate. Any functional output passing both policy suites
sets `invalid_task_or_tests`.

## Immutability rules

Every command writes new files only and refuses to overwrite. Requests, raw model text, extracted
plans, candidates, evaluations, and reports are bound by SHA-256 to the run manifest; a changed
config, task, dataset, or adapter aborts the consuming command. All files are written with LF
newlines so hashes agree across Windows and POSIX. `--dry-run` on `run-stage2-eval` uses an
offline stand-in generator for wiring checks only and its outputs must never be reported.
