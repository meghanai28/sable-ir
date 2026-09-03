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
