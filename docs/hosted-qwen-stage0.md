# Hosted Qwen Stage 0 runbook

Stage 0 is pinned to Alibaba Cloud Model Studio's `qwen3.6-27b` model in the Singapore region. The
client uses the native DashScope multimodal-generation endpoint with text-only input and SSE
streaming. Every request explicitly sets thinking mode: the first six conditions disable it and the
two native-thinking conditions enable it.

No command below contacts Alibaba unless it is the `generate-stage0` command **without**
`--dry-run`.

## Before account approval

Validate configuration and inspect credential readiness:

```bash
uv run sable-ir validate-config config/stage0.toml
uv run sable-ir qwen-preflight
```

Freeze all 40 requests without credentials or API calls:

```bash
uv run sable-ir prepare-stage0 --run-id stage0-smoke-20260902
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --dry-run
```

Preparation snapshots the exact task prompt, wire prompt, model parameters, seed, task hash, four
test-suite hashes, request-file hash, condition, assigned policy, sandbox, and continuation
thresholds for every job. Preparing into a non-empty directory is refused.

## After account approval

Create a Singapore-region Model Studio API key and export it only in the current shell:

```bash
export DASHSCOPE_API_KEY='sk-...'
uv run sable-ir qwen-preflight
```

Run one billable canary request first:

```bash
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --limit 1
```

Inspect its `result.json`, raw SSE response, and extracted candidate before resuming all jobs:

```bash
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json
```

Completed jobs are skipped. Provider failures are recorded as immutable attempt artifacts and
transient failures use bounded exponential retry. API keys are used only in the Authorization
header and are never written to request, response, manifest, or error artifacts.

Evaluate the canary, then the complete run, using the Docker boundary:

```bash
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --limit 1
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json
```

Create a final report only after all 40 jobs have evaluation artifacts:

```bash
uv run sable-ir report-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --report-id final
```

See [the scoring runbook](stage0-scoring.md) for metric definitions and gate semantics.

## Artifact layout

```text
artifacts/stage0/<run-id>/
├── manifest.json
└── jobs/<task>__<condition>__s00/
    ├── request.json
    ├── result.json
    ├── evaluation.json
    ├── attempts/attempt-01.json
    ├── responses/response-01.json
    ├── candidates/candidate-01.py
    └── reasoning/reasoning-01.txt
```

`reasoning/` is created only when the provider returns reasoning content. Token usage records input,
output, total, and reasoning tokens separately. A `finish_reason` of `length` is retained as a
truncated generation instead of silently being treated as complete.
