# sable-ir

This repository implements the staged experiment described in the accompanying proposal. The
current checkpoint contains the completed Stage 0 scaffold and the Stage 1A hosted-Kimi
planner-to-renderer generation pipeline. The activation-hook smoke test remains a later checkpoint.

## Development

The project uses Python 3.11+ and `uv`:

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy
```

Validate the checked-in Stage 0 configuration:

```bash
uv run sable-ir validate-config config/stage0.toml
```

Validate one or more task JSON files (added in the task-corpus checkpoint):

```bash
uv run sable-ir validate-task tasks/example.json
```

Evaluate model-generated Python with the Docker sandbox:

```bash
uv run sable-ir evaluate tasks/example.json candidate.py
```

Audit the complete Stage 0 corpus, including both reference implementations against the expected
A/B cross-test matrix:

```bash
uv run sable-ir audit-tasks
```

The five task specifications record revision-pinned CWEval provenance and adaptation notes. Each
contains an exact upstream benchmark anchor, a policy-neutral adapted surface request, two
length-matched six-clause documents, independent executable suites, and policy-A and policy-B
reference implementations. The corpus audit also requires the applicable clause to occupy
positions 1 through 5 exactly once and documents to stay within the 150–250 approximate-token
target.

Docker execution has networking disabled, a read-only root and bind mount, dropped Linux
capabilities, `no-new-privileges`, an unprivileged user, a private `tmpfs`, and CPU, memory, PID,
output, source-size, and wall-time limits. Compilation happens before tests; each applicable suite
runs in a fresh container. Adapted jobs run all four suites, while exact upstream-anchor jobs run
functionality and original-security suites only. The `--unsafe-local` option is only for trusted
development fixtures and never activates automatically.

Stage 0 is pinned to Moonshot AI's hosted `kimi-k2.6` through its international
OpenAI-compatible Chat Completions endpoint. Configuration stores environment-variable **names**,
never API keys. Runtime artifacts belong under `artifacts/` and are ignored by Git.

The complete account-preflight, request-freezing, canary, resume, and artifact instructions are in
[the hosted Kimi runbook](docs/hosted-kimi-stage0.md).

The proposal-to-implementation trace and audited scoring decisions are recorded in
[the Stage 0 compliance sweep](docs/stage0-compliance.md).

Hosted Kimi results establish only the Stage 0 behavioral phenomenon. Before activation probing
or causal intervention, that phenomenon must be reproduced on the selected local open-weight
model; mechanistic claims apply only to that local model, not to hosted Kimi.

After generation, evaluate every candidate and create the gate report:

```bash
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json
uv run sable-ir report-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --report-id final
```

That report leaves the semantic dataset audit pending. Add the explicit reviewer and two audit
results from the scoring runbook to permit a `continue_to_stage1` recommendation.

The scoring formulas, thresholds, provenance checks, dataset audit, and final-state precedence are
specified in [the Stage 0 scoring runbook](docs/stage0-scoring.md).

Stage 1A freezes 180 thinking-enabled plan requests and, after those plans finish, 720 fresh
non-thinking renderer requests. The exact five-task pilot matrix, Stage 0 lineage checks, learned
token/time ceilings, failure behavior, and commands are documented in
[the hosted Kimi Stage 1A runbook](docs/hosted-kimi-stage1a.md).

Exact length matching, blinded plan labels, behavioral metrics, renderer-dependence controls, and
the continuation state machine are documented in [the Stage 1B–E runbook](docs/stage1-bcde.md).

Stage 2 trains a language-model-only QLoRA planner adapter on pinned Qwen3.5-4B (9B fallback) on
the Windows RTX 5080 PC, with a frozen base-task split, a behavior-blinded reference audit,
dev-only checkpoint selection, and local post-SFT frontier reports. Install with
`uv sync --extra dev --extra stage2` on that machine; the commands and 16 GiB budget are in
[the Stage 2 planner SFT runbook](docs/stage2-planner-sft.md).

Stage 3 records three aligned boundary states on the local planner and frozen renderer, labels
naturally generated plans for clause selection and visible policy retention, and fits localization
probes plus task-balanced policy directions. Install with
`uv sync --extra dev --extra stage2 --extra stage3` on the GPU PC (the `stage3` extra is CPU-only
and also works on the Mac). The commands, paraphrase split, and interpretation table are in
[the Stage 3 information-tracing runbook](docs/stage3-information-tracing.md).

For a single Windows handoff that tells an execution agent how to run and audit Stages 2–5 in
order, use [the Claude PC handoff](docs/pc-claude-stages2-5-handoff.md).

## Results and audit packets

Stage 3 returned a **negative preregistered gate**: the A/B policy distinction is not a
paraphrase-robust linearly decodable variable at renderer ingestion, so no causal intervention was
run and Stage 4 was not executed. The full result, with its postmortem diagnostics and caveats, is
in [the Stage 3 results report](docs/stage3-results.md). Stage 5 requires a complete Stage 4 report
and so was not run either; the blocker, and which of its intended outputs are already covered
elsewhere, are recorded in [Stage 5 was not run](docs/stage5-not-run.md).

Every document below exists in two forms. The Markdown renders on GitHub and is the canonical,
reviewable-in-PR version. The hosted page is the same content rendered for reading and, for the
labelling packets, with click-to-label controls; those pages are **private until shared from each
page's own share menu**, so the Markdown is the version to rely on.

| Document | Markdown (canonical) | Hosted page |
| --- | --- | --- |
| Stage 3 results and negative gate | [docs/stage3-results.md](docs/stage3-results.md) | [view](https://claude.ai/code/artifact/973cbddb-6a0c-406c-a1ba-1150c82e926b) |
| Why Stage 5 was not run | [docs/stage5-not-run.md](docs/stage5-not-run.md) | — |
| Stage 2 reference audit: 20 plans, 15 paraphrases, 40 phrasings | [docs/stage2-reference-audit-packet.md](docs/stage2-reference-audit-packet.md) | [view](https://claude.ai/code/artifact/0fad2006-9c4e-466f-9b4a-9dfa4e67dce3) |
| Stage 3 primary plan audit: all 240 rows | [docs/stage3-primary-audit-packet.md](docs/stage3-primary-audit-packet.md) | [view](https://claude.ai/code/artifact/d2a6dcca-5b40-4ccc-a10a-6ec5af30bbc1) |
| Stage 2 held-out plan audit (36 rows, labelling tool) | — | [view](https://claude.ai/code/artifact/9fbc2f6c-4ff2-496b-a56f-39ca7e288973) |
| Stage 3 double audit (96 rows, labelling tool) | — | [view](https://claude.ai/code/artifact/5a0a1437-a209-41b1-99f6-0a54740de4dd) |

The two labelling tools have no Markdown equivalent because their value is the interface; their
content is a subset of the packets above, and their completed labels are already written into
`plan-audit.json` and `plan-audit.double.json`.

One exclusion is worth knowing before you run the verifier: the trained adapter weights
(`adapter_model.safetensors`, 233 MB each) are **not in this repository**. GitHub rejects files
over 100 MB and Git LFS free quota is 1 GB, so they stay on the run machine. Their SHA-256 values
are still recorded in `artifacts/stage2/selection.json` and `training-result.json`. On a fresh
clone the verifier therefore reports `selection_lineage` and `eval_lineage_*` as failing for want
of the files; every other check passes from repository bytes alone.

To recompute the whole chain from repository bytes rather than trusting any reported number:

```bash
uv run sable-ir verify-audit-packet
```

It re-derives the 20-plan to 240-row expansion, re-hashes every audit row, checks the 144/48/48
dataset counts and file hashes, confirms the human attestations still bind the audited bytes, and
re-derives training, checkpoint-selection and evaluation lineage. It exits non-zero on any
disagreement.
