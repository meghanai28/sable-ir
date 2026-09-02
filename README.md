# sable-ir

This repository implements the staged experiment described in the accompanying proposal. The
current checkpoint contains the Stage 0 scaffold, sandbox, five-task A/B corpus, hosted-Qwen
generation path, and continuation-gate scorer. The activation-hook smoke test remains a later
checkpoint.

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

The five task specifications record their CWEval provenance and adaptation notes. Each contains a
policy-neutral surface request, two length-matched six-clause documents, four independent test
suites, and policy-A and policy-B reference implementations. The corpus audit also requires the
applicable clause to occupy positions 1 through 5 exactly once.

Docker execution has networking disabled, a read-only root and bind mount, dropped Linux
capabilities, `no-new-privileges`, an unprivileged user, a private `tmpfs`, and CPU, memory, PID,
output, source-size, and wall-time limits. Compilation happens before tests; each of the four suites
runs in a fresh container. The `--unsafe-local` option is only for trusted development fixtures and
never activates automatically.

Stage 0 is pinned to Alibaba Cloud Model Studio's hosted `qwen3.6-27b` through the native DashScope
endpoint. Configuration stores environment-variable **names**, never API keys. Runtime artifacts
belong under `artifacts/` and are ignored by Git.

The complete account-preflight, request-freezing, canary, resume, and artifact instructions are in
[the hosted Qwen runbook](docs/hosted-qwen-stage0.md).

After generation, evaluate every candidate and create the gate report:

```bash
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json
uv run sable-ir report-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --report-id final
```

The scoring formulas, thresholds, provenance checks, and the one required manual review are
specified in [the Stage 0 scoring runbook](docs/stage0-scoring.md).
