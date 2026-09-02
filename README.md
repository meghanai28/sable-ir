# sable-ir

This repository implements the staged experiment described in the accompanying proposal. The
current checkpoint contains the repository scaffold and the validated schemas/configuration for
Stage 0. Later checkpoints add the execution harness, task corpus, hosted generation, gate report,
and activation-hook smoke test.

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
