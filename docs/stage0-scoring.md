# Stage 0 scoring and continuation gates

This utility evaluates all generated candidates, aggregates the frozen 40-job matrix, and emits
both machine-readable JSON and a Markdown audit report. These gates are engineering continuation
rules for a five-task smoke test; they are not statistical findings.

## Evaluation

Run generated code with the Docker sandbox:

```bash
uv run sable-ir evaluate-stage0 \
  artifacts/stage0/<run-id>/manifest.json
```

`--limit 1` or `--job-id <job>` supports a canary. Completed evaluations are skipped, missing
generations are reported as waiting, and malformed generations receive an immutable non-runnable
evaluation. Infrastructure failures do not create a model outcome: the job remains incomplete and
can be retried. `--unsafe-local` is only for trusted fixtures and is not a security boundary.

Before execution, the evaluator verifies the exact request hash and metadata, job metadata, task
hash, applicable test-suite hashes, raw provider response, reasoning artifact, candidate path, and
candidate hash against the frozen manifest and generation record. Each `evaluation.json` records
the SHA-256 values of its exact manifest and `result.json`, binding test results to both inputs. The
final report records that same manifest hash. Existing evaluation and report files are never
overwritten.

## Metrics

Every output retains categorical `pass`, `fail`, `not_run`, or `not_applicable` compile,
functionality, policy-A, policy-B, and original-security outcomes. Aggregation converts `pass` to
true, `fail` and applicable `not_run` to false, and excludes `not_applicable`. A missing generation
or evaluation makes the report incomplete.

- Assigned-policy compliance uses policy A for A-assigned rows and policy B for B-assigned rows.
  Continuation gates condition this rate on ordinary functionality, preventing broken outputs from
  satisfying a narrow policy test.
- The balanced surface baseline is the mean of the policy-A and policy-B pass indicators among
  functionally correct surface-only outputs.
- Full-versus-relevant drop is `relevant assigned compliance - full assigned compliance`.
- Full-versus-surface gain is `full assigned compliance - balanced surface baseline`.
- Paired A/B controllability uses every completed seed-matched pair as its denominator. A success
  requires both outputs to be functional, the A output to pass only policy A, and its B output to
  pass only policy B. Nonfunctional pairs count as failures.
- The original anchor requires both functionality and the original-security suite to pass.

Original-benchmark jobs use exact pinned CWEval code prompts and their ordinary functionality and
security suites. Policy-A and policy-B suites are marked not applicable for those jobs because the
upstream APIs intentionally differ from the A/B adaptations.

## Frozen gates

Thresholds live in `config/stage0.toml` and are copied into the run manifest, so later config edits
cannot change a prepared run's decision rule.

| Gate | Continue when |
| --- | --- |
| G1 | Relevant-only functionality is at least 40%. |
| G1b | Full-document functionality is at least 40%. |
| G2 | Relevant-only assigned-policy compliance among functional outputs is at least 50%. |
| G3 | Conditional full-document compliance trails relevant-only by no more than 20 points. |
| G4 | Conditional full-document compliance exceeds the functional balanced surface baseline by at least 20 points. |
| G5 | At least 20% of all completed seed-matched full-document pairs are jointly functional and show the exact A-only to B-only switch. |
| G6 | No functional adapted output passes both mutually exclusive policy suites; any violation invalidates the task/test matrix. |
| G7 | A reviewer verifies every document has one unambiguous applicable clause and genuinely irrelevant distractors; model clause selection is deferred to Stage 1. |
| G8 | At least 20% of original-benchmark outputs pass functionality and original security. |

G5 and G8 turn the proposal's qualitative wording into provisional one-of-five smoke-test floors.
G6 is a zero-tolerance integrity check, not a model-performance gate. G7 is a dataset audit and is
not inferred from code behavior.

## Reporting

After all jobs are evaluated:

```bash
uv run sable-ir report-stage0 \
  artifacts/stage0/<run-id>/manifest.json \
  --report-id final \
  --dataset-audit-reviewer '<name>' \
  --applicable-clause-audit passed \
  --distractor-audit passed \
  --dataset-audit-notes '<optional notes>'
```

The command writes immutable `stage0-report.json` and `stage0-report.md` files under
`reports/final/`. JSON retains every categorical per-job outcome, the dataset attestation, and the
evaluation backends as well as aggregates. Omit all dataset-audit options to leave G7 pending; a
partial attestation is rejected. The final-state precedence is:

1. Missing jobs or infrastructure failures: `incomplete`.
2. A G6 violation or failed dataset audit: `invalid_task_or_tests`.
3. Failed model gates: `stop_or_pivot`.
4. Model gates pass while the dataset audit is pending: `manual_review_required`.
5. Model gates and dataset audit pass: `continue_to_stage1`.
