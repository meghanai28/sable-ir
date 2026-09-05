# Stage 3 result figures

These figures are descriptive views of the immutable Stage 3 activation, audit, probe,
selection, held-out, and completion artifacts. The packet does not recompute or replace the
canonical Stage 3 report.

## Key result

`01-key-stage3-evidence` is the recommended main figure. It shows the held-out boundary probes,
the primary omitted/blurred renderer-ingestion analysis against text controls, and the frozen
Stage 4 authorization decision.

Suggested sentence beneath the figure:

> On the single held-out archive task, renderer-ingestion activations did not decode the assigned
> policy on omitted/blurred plans (AUROC 0.485), did not outperform the best text control, and did
> not yield an aligned cross-task policy-orientation direction, so Stage 4 was not authorized.

## Supporting figures

1. `02-heldout-probe-transfer`: pooled and disjoint-paraphrase probe performance by boundary.
2. `03-renderer-controls`: renderer activation versus text, metadata, and negative controls.
3. `04-dev-layer-selection`: dev-only layer-selection curves; these are not held-out evidence.
4. `05-task-direction-alignment`: task-level A/B direction cosines across layers.
5. `06-quadrants-and-support`: quadrant composition and held-out denominator support.
6. `07-plan-audit-quality`: behavior-blinded audit reliability and plan-label outcomes.

Each figure has PNG and SVG versions. The matching CSV contains its plotted source values.
`figure-manifest.json` records exact SHA-256 hashes for all canonical sources and generated files.

## Interpretation boundary

Stage 3 is a five-task pilot with only one dev task and one held-out test task. A negative Stage 3
result blocks the preregistered causal intervention; it does not invalidate the Stage 0 or Stage 1
behavioral findings. Pooled scores containing explicit policy text are localization diagnostics,
not the primary mechanistic result.
