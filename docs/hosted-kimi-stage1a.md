# Hosted Kimi Stage 1A runbook

This checkpoint implements Section VI.A of the proposal as a five-task pilot over the exact task
revisions that passed Stage 0. It does not claim to be the future six-task development split.

## Frozen matrix

- 5 source tasks
- 2 assigned policies (A and B)
- 2 independently generated formats (structured and free-form)
- 3 concision instructions (full, concise, and minimal)
- 3 planner samples per cell
- 4 fresh renderer samples from each exact plan
- 180 thinking-enabled planner requests
- 720 non-thinking renderer requests
- functionality, policy-A, policy-B, and adapted anchor-security tests for all 720 renders

Every plan ends in `END_PLAN`. Structured plans contain SOURCE, TRUST, SINK, GUARD, ORDER, and
EFFECT exactly once and in that order. Free-form plans are generated independently; this is not
the information-matched paired-format control from a later part of Stage 1.

## Bounds learned from Stage 0

Stage 0 non-thinking code outputs used at most 936 tokens, so renderers retain a 4,096-token
ceiling. Thinking outputs reached 21,867 output tokens and 535 seconds, so planners receive the
approved 32,768-token ceiling and every stream receives 900 seconds. Requests are paced at a
25-second start-to-start interval. The provider is called at most once per job, automatic retries
are disabled, and the first provider error trips a circuit breaker.

The 32K value is a safety ceiling, not a requested plan length. Plans are allowed to finish, and
compression is measured from provider-reported observed output accounting rather than by
truncating a nominal length bucket.

## Preparation and execution

Load the locally ignored credential and perform the request-free preflight:

```bash
set -a
source .env.stage0.local
set +a
uv run sable-ir stage1-kimi-preflight
```

Freeze the plan matrix:

```bash
uv run sable-ir prepare-stage1-plans --run-id stage1a-plans-20260902
```

Run one explicit canary, inspect its immutable result and plan, and then authorize the remaining
matrix with the exact run ID:

```bash
uv run sable-ir generate-stage1-plans \
  artifacts/stage1/stage1a-plans-20260902/manifest.json \
  --job-id path_symlink_report__plan_a__structured__full__p00

caffeinate -i uv run sable-ir generate-stage1-plans \
  artifacts/stage1/stage1a-plans-20260902/manifest.json \
  --all --confirm-full-run stage1a-plans-20260902
```

Only after all 180 plans are complete, freeze the exact plan-to-renderer handoffs:

```bash
uv run sable-ir prepare-stage1-renders \
  artifacts/stage1/stage1a-plans-20260902/manifest.json \
  --run-id stage1a-renders-20260902
```

Run one renderer canary and its sandbox evaluation, then run and evaluate the rest:

```bash
uv run sable-ir generate-stage1-renders \
  artifacts/stage1/stage1a-renders-20260902/manifest.json \
  --job-id path_symlink_report__render_a__structured__full__p00__r00

uv run sable-ir evaluate-stage1-renders \
  artifacts/stage1/stage1a-renders-20260902/manifest.json \
  --job-id path_symlink_report__render_a__structured__full__p00__r00

caffeinate -i uv run sable-ir generate-stage1-renders \
  artifacts/stage1/stage1a-renders-20260902/manifest.json \
  --all --confirm-full-run stage1a-renders-20260902

caffeinate -i uv run sable-ir evaluate-stage1-renders \
  artifacts/stage1/stage1a-renders-20260902/manifest.json
```

Write the Part A completion record:

```bash
uv run sable-ir status-stage1a \
  artifacts/stage1/stage1a-plans-20260902/manifest.json \
  --render-manifest artifacts/stage1/stage1a-renders-20260902/manifest.json \
  --output artifacts/stage1/stage1a-part-a-status.json
```

The status is complete only when all 180 plans and 720 renders are generated without truncation
or malformed output, all 720 renders are evaluated, and non-thinking renderer responses contain
no visible `reasoning_content`.

## Failure handling

Do not rerun the same manifest after a provider failure: the failed job has spent its only
authorized attempt. Preserve its attempt artifact, inspect the error, and create an explicit
lineage-linked recovery before authorizing another paid request. Never raise the stream ceiling
above 900 seconds for a slow condition. Infrastructure failures during Docker evaluation are
incomplete and retryable; they are not model failures.
