# Hosted Kimi Stage 0 runbook

Stage 0 is pinned to Moonshot AI's hosted `kimi-k2.6` model at the international API base URL
`https://api.moonshot.ai/v1`. The client uses the OpenAI-compatible Chat Completions endpoint with
SSE streaming. Every request explicitly sets `thinking.type`: the first six conditions disable
thinking and the two native-thinking conditions enable it.

No command below contacts Kimi except `generate-stage0` without `--dry-run`. Never paste an API
key into source files, artifacts, commands recorded in documentation, or chat. If a key has been
disclosed, revoke it and create a replacement before any live run.

## Before using a credential

Validate configuration and inspect credential readiness without a network call:

```bash
uv run sable-ir validate-config config/stage0.toml
uv run sable-ir kimi-preflight
```

Install the pinned sandbox image separately so image-download time can never be mistaken for a
candidate timeout:

```bash
docker pull 'python@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7'
```

Production evaluation uses `--pull=never` and fails as retryable infrastructure setup if that
exact image is absent. The source tag was `python:3.12.11-slim-bookworm`; execution uses its
immutable repository digest directly because Docker Desktop's local store resolves `python@digest`
but not the redundant `python:tag@digest` spelling. The manifest also pins `platform: linux/arm64`;
this digest is the resolved ARM64 image used on the experiment machine.

Freeze all 40 requests without credentials or API calls:

```bash
uv run sable-ir prepare-stage0 --run-id stage0-smoke-20260902
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --dry-run
```

Preparation snapshots the exact task and wire prompts, model settings, explicit pairing metadata,
task hash, upstream revision/task/prompt hash, applicable test-suite hashes, generation/evaluation
harness versions, request-file hash, condition, assigned policy, sandbox, and continuation
thresholds. Adapted jobs bind all four suites; upstream anchors bind functionality and
original-security suites. Preparing into a non-empty directory is refused.

Original-anchor and surface-only jobs record `pair_id: null`. A/B jobs record a stable
`<task>__<condition-pair>__pair_<sample>` identifier, so relevant-only, full-document, and
native-thinking comparisons are three distinct pairs. Every job records
`provider_seed_supported: false` and `provider_seed_sent: null`; these metadata fields are not sent
to Kimi. The provider request does not contain `seed`, `temperature`, or `top_p`. Non-thinking
requests are capped at 4,096 completion tokens; thinking requests are capped at 16,384 total
completion/reasoning tokens.
The client also closes a response after 300 seconds, 8 MiB, or 100,000 SSE events, whichever
limit is reached first; an individual blocked socket read times out after 120 seconds.

## Credential and two-canary sequence

Export a newly rotated key only in the current shell, then run the request-free preflight:

```bash
export MOONSHOT_API_KEY='<new key>'
uv run sable-ir kimi-preflight
```

Run exactly one non-thinking upstream-anchor canary:

```bash
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --job-id path_symlink_report__original_benchmark__s00
```

Inspect its `result.json`, raw SSE response, and extracted candidate. Evaluate it with Docker:

```bash
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --job-id path_symlink_report__original_benchmark__s00
```

Only if that call and artifact are sound, run the native-thinking canary:

```bash
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --job-id path_symlink_report__native_thinking_full_document_a__s00
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --job-id path_symlink_report__native_thinking_full_document_a__s00
```

Confirm that the thinking result contains reasoning content and sensible token usage. After both
canaries have `result.json` and `evaluation.json` artifacts and have been manually audited, unlock
the remaining jobs with the exact run ID:

```bash
uv run sable-ir generate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json \
  --all \
  --confirm-full-run stage0-smoke-20260902
```

Completed jobs are skipped. Each job is allowed one provider attempt across the lifetime of the
frozen run; there are no automatic retries. Any provider error, timeout, invalid UTF-8, incomplete
SSE stream, response-limit breach, missing usage, or model mismatch stops the invocation before a
later job can be sent. Prepare a new run only after inspecting a failed attempt artifact. The API
key is used only in the Authorization header and is never written to request, response, manifest,
or error artifacts.

## Evaluation and report

Evaluate the complete run using the Docker boundary:

```bash
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/stage0-smoke-20260902/manifest.json
```

Docker-launch, corrupted-evaluator, and other infrastructure failures leave the affected job
incomplete instead of creating a model failure. Correct the environment and rerun evaluation;
completed evaluation artifacts are skipped.

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
`manual_review_required`. A partial attestation is rejected. See
[the scoring runbook](stage0-scoring.md) for metric definitions and gate semantics.

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
truncated generation rather than silently treated as complete.

The exact raw response file is SHA-256-bound into `result.json`; evaluation revalidates the raw
response, combined content, token usage, extracted candidate, and optional reasoning artifact.
