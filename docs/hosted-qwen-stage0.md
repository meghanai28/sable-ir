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

Preparation snapshots the exact task prompt, wire prompt, model parameters, seed, task hash,
applicable test-suite hashes, request-file hash, condition, assigned policy, sandbox, and
continuation thresholds for every job. Adapted jobs bind all four suites; upstream-anchor jobs bind
functionality and original-security suites. Preparing into a non-empty directory is refused.

## After account approval

Create a Singapore-region Model Studio API key and export it only in the current shell:

```bash
export DASHSCOPE_API_KEY='sk-...'
uv run sable-ir qwen-preflight
```

Run one non-thinking upstream-anchor canary first:

```bash
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --job-id path_symlink_report__original_benchmark__s00
```

Inspect its `result.json`, raw SSE response, and extracted candidate. Then run one targeted
native-thinking canary and verify that `reasoning_characters` and `reasoning_tokens` are nonzero:

```bash
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --job-id path_symlink_report__native_thinking_full_document_a__s00
```

Evaluate exactly those canaries with Docker:

```bash
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --job-id path_symlink_report__original_benchmark__s00
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --job-id path_symlink_report__native_thinking_full_document_a__s00
```

If both artifacts look correct, resume all jobs:

```bash
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json
```

Completed jobs are skipped. Provider failures are recorded as immutable attempt artifacts and
transient failures use bounded exponential retry. API keys are used only in the Authorization
header and are never written to request, response, manifest, or error artifacts.

Evaluate the complete run using the Docker boundary:

```bash
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json
```

Docker-launch, corrupted-evaluator, and other infrastructure failures leave the affected job
incomplete rather than creating a model failure. Correct the environment and rerun the same
command; completed evaluation artifacts are skipped.

Create a final report only after all 40 jobs have evaluation artifacts and manually auditing every
safety document for one unambiguous applicable clause and genuinely irrelevant distractors:

```bash
uv run sable-ir report-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --report-id final \
  --dataset-audit-reviewer '<name>' \
  --applicable-clause-audit passed \
  --distractor-audit passed
```

Omitting all three audit options records the audit as pending and can produce only
`manual_review_required`. A partial attestation is rejected.

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

The exact raw response file is SHA-256-bound into `result.json`; evaluation revalidates the raw
response, combined content, token usage, extracted candidate, and optional reasoning artifact.
