# Stage 3 design-correction audit — 2026-09-03

Status: corrections implemented before any activation capture. No new experimental condition or
data requirement was added.

## Finding 1: invalid three-vector probe training

Resolved. Probe rows are all training activations from paraphrase set 1. `task_balanced_weights`
gives every `(base task, policy)` group equal total weight. Task-level A/B difference vectors are
used only for direction estimation and cross-task alignment. Report uncertainty is a bootstrap of
base-task summaries; activation rows are never independent uncertainty units. With one test task,
the held-out result is explicitly a case study and its task-cluster interval is unavailable.

Machine-auditable report fields:

- `probe_training_unit = activation_row`
- `probe_task_weighting = equal_total_weight_per_base_task`
- `direction_estimation_unit = task_level_ab_difference_only`
- `uncertainty_unit = base_task_cluster`
- every metric records `independent_task_clusters` and `aggregation`

## Finding 2: weak Stage 4 authorization

Resolved. `causal_evaluation_authorized` is true only when all four exact requirements pass:

1. renderer-ingestion decodability;
2. renderer-ingestion transfer to paraphrase set 2;
3. renderer-ingestion task-level direction alignment; and
4. complete activation/evaluation/label data.

Planner-input and planner-output probes appear only as information-loss localization and cannot
unlock Stage 4. `probe_generalizes` now refers only to renderer-ingestion decodability plus set-2
transfer.

## Finding 3: pooled probe accuracy as headline

Resolved. The primary result is renderer ingestion on test plans labeled `omitted` or `ambiguous`
(reported as `blurred`). It is compared against the surface-only control and visible-text/length
models. Hidden-use and false-certificate quadrants are separate. Each subset requires at least 10
rows and both A/B labels; otherwise its exact state is `insufficient_quadrant_support`. Pooled
accuracy remains a secondary localization diagnostic and is never substituted for an unsupported
quadrant.

## Terminology and control provenance

Across unrelated vulnerability families, reports use **policy-orientation direction**. The only
fact-specific transfer is the symlink-policy comparison from `path_symlink_report` to
`path_symlink_archive`.

During implementation validation, one additional provenance bug was found and fixed: Stage 3 had
materialized auxiliary directions only at the probe-selected layer. It now freezes layer-qualified
paraphrase, lexical, format, and random controls at every layer Stage 4 may use, including the
selected causal layer and preregistered early layer. A control from a different depth can no longer
be mislabeled as matched.

## Preserved approved design

The pilot labeling, 3/1/1 task split, three capture boundaries, disjoint paraphrase sets, both
lexical framings, behavior-blinded audits, frozen layer/C selection, surface/text/length/framing/
shuffled-label controls, skipped clause-position probe with only three training tasks, Stage 1
provisional-state logic, adapter-disabled renderer, and VRAM-as-implementation-check are unchanged.

Static enforcement lives in `config/stage3.toml`, `src/sable_ir/stage3.py`, and
`src/sable_ir/stage3_analysis.py`; the operational sequence is in
`docs/stage3-information-tracing.md`.
