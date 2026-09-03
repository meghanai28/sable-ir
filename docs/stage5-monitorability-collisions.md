# Downstream monitorability, policy-collision, and evaluation pipeline

This stage is analysis-only. Run it after the canonical Stage 1 report, Stage 2 model-floor and
final-test reports, complete Stage 3 dataset/report, and complete Stage 4 report exist at the paths
in [config/stage5.toml](../config/stage5.toml). It never calls Kimi, loads Qwen, generates text,
executes generated code, or edits an earlier artifact. Every input is SHA-256-bound before analysis.

Hosted Kimi and local Qwen are separate strata. Their rows, HU+ baselines, uncertainty, and claims
are never pooled. The base task is always the independent cluster; renderer draws quantify
within-task stochasticity. With five tasks, all cross-task estimates are explicitly a pilot.

## 1. Freeze and normalize completed inputs

Run from the repository root on macOS, Linux, or the PC. No GPU is needed.

```powershell
uv run sable-ir validate-stage5-config
New-Item -ItemType Directory -Force artifacts\stage5\analysis-01 | Out-Null
uv run sable-ir prepare-stage5-inputs --run-id analysis-01 `
  --output artifacts\stage5\analysis-01\input-manifest.json
uv run sable-ir assemble-stage5-observations `
  artifacts\stage5\analysis-01\input-manifest.json `
  --output artifacts\stage5\analysis-01\observations.json
```

Preparation refuses missing/incomplete stages, a noncanonical Stage 1 result, provisional Stage 2/3
standing, invalid mutually exclusive A/B suites, incomplete manual audits, a Stage 4 incomplete
state, or any hash mismatch. The normalized artifact retains raw categorical outcomes (`pass`,
`fail`, `not_run`, `not_applicable`) and converts them to booleans only inside each aggregation.

## 2. Automatic metrics and ambiguity

```powershell
uv run sable-ir report-stage5-metrics `
  artifacts\stage5\analysis-01\observations.json `
  --output artifacts\stage5\analysis-01\metrics.json
uv run sable-ir index-stage5-collisions `
  artifacts\stage5\analysis-01\observations.json `
  --output artifacts\stage5\analysis-01\collision-index.json
```

The report contains raw numerators and denominators, pooled descriptive rates, task-balanced rates,
and task-clustered bootstrap intervals. It reports:

- visible assigned-policy retention, HU+ separately for A/B, and the paired per-task A/B average;
- false certificates, assigned behavior under invisible policy, and visible-plan policy failures;
- compilation, functionality, assigned-and-functional, opposite-policy, and original-security
  outcomes;
- exact clause-selection precision/recall, irrelevant-clause inclusion, and confident-wrong-clause
  behavior;
- plan-length curves for retention, policy behavior, functionality, clause recall, and false
  certificates;
- exact-plan A/B counts, assigned compliance, both/neither rates, collision status, qA, and AAB;
  AAB is `insufficient_support` unless at least eight functional A-or-B-classifiable outputs exist.

One functional output passing both mutually exclusive suites changes the report to
`invalid_task_or_tests` and blocks collision interpretation. Stage 1/2/3 plans usually have fewer
than eight renderer draws and are retained as excluded diagnostics; Stage 4's 16 unpatched draws can
meet the ambiguity floor. Low ambiguity is always displayed beside assigned-policy compliance, so
consistent implementation of the wrong policy cannot look successful.

Length curves intentionally do not automatically declare whether visibility failed “first.” No
numeric failure threshold was preregistered in the proposal, so the table says
`descriptive_only_no_preregistered_failure_threshold` and leaves that scientific interpretation for
the audited report.

## 3. Freeze the collision vocabulary without held-out leakage

The development command exposes only train/dev natural collision pairs and writes immutable unified
diffs. It cannot emit a test diff.

```powershell
uv run sable-ir prepare-stage5-development-collision-audit `
  artifacts\stage5\analysis-01\collision-index.json `
  --output artifacts\stage5\analysis-01\development-collision-audit.json `
  --diff-directory artifacts\stage5\analysis-01\development-diffs
```

For each row, inspect the diff and fill the first policy-relevant behavioral divergence. Use the
matching family-specific ID and exact definition from
[data/stage5/collision-rubric.json](../data/stage5/collision-rubric.json) when one applies; otherwise
create a snake-case development category and stable definition. Also fill the smallest extra plan
distinction and IDs of any other collisions explained by it. Then fill `reviewer` and `completed_at`.
Do not inspect held-out outputs.

```powershell
uv run sable-ir freeze-stage5-collision-taxonomy `
  artifacts\stage5\analysis-01\development-collision-audit.json `
  --output artifacts\stage5\analysis-01\frozen-taxonomy.json
uv run sable-ir prepare-stage5-heldout-collision-audit `
  artifacts\stage5\analysis-01\collision-index.json `
  artifacts\stage5\analysis-01\frozen-taxonomy.json `
  --output artifacts\stage5\analysis-01\heldout-collision-audit.json `
  --diff-directory artifacts\stage5\analysis-01\heldout-diffs
```

Only after the taxonomy hash exists does the second command expose test collisions. For each held-out
row, fill the same divergence fields and set `covered_by_frozen_taxonomy`. A covered row must repeat
the exact frozen ID and definition; a new row must use an ID absent from the frozen taxonomy. The
primary taxonomy is never retroactively edited.

```powershell
uv run sable-ir report-stage5-collision-vocabulary `
  artifacts\stage5\analysis-01\collision-index.json `
  artifacts\stage5\analysis-01\development-collision-audit.json `
  artifacts\stage5\analysis-01\frozen-taxonomy.json `
  artifacts\stage5\analysis-01\heldout-collision-audit.json `
  --output artifacts\stage5\analysis-01\collision-vocabulary.json
```

This produces top-1/3/5 held-out coverage, new-distinction rate, category accumulation, and category
recurrence across independent base tasks. Because the proposal gives qualitative but not numerical
closed-set thresholds, the software reports the measurements without manufacturing a binary
small-set/long-tail gate.

## 4. Final evaluation record and plot-ready tables

```powershell
uv run sable-ir report-stage5-final `
  artifacts\stage5\analysis-01\metrics.json `
  artifacts\stage5\analysis-01\collision-vocabulary.json `
  --output artifacts\stage5\analysis-01\final-report.json
uv run sable-ir export-stage5-tables `
  artifacts\stage5\analysis-01\metrics.json `
  artifacts\stage5\analysis-01\collision-vocabulary.json `
  artifacts\stage5\analysis-01\final-report.json `
  --output-directory artifacts\stage5\analysis-01\tables
```

The final report binds the monitorability, vocabulary, information-localization, causal, and
bottleneck criteria to exact Stage 2/3/4 reports. The CSV export is a representation-only step; it
does not recompute statistics. It writes source summary, length curve, ambiguity, task-level HU+,
collision vocabulary, and core-criteria tables for figures and the final write-up.

Every command refuses overwrite. Use a new analysis run ID if any earlier stage is rerun. Empty
development or held-out collision sets are valid and yield an empty frozen taxonomy or
`no_heldout_collisions`, never a fabricated rate.
