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

Configuration stores environment-variable **names**, never API keys. Runtime artifacts belong under
`artifacts/` and are ignored by Git.

