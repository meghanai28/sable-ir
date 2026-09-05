# Stage 0 final figures

Source: `artifacts/stage0/stage0-smoke-20260902-timeout-recovery/reports/final/stage0-report.json`.

All charts are descriptive summaries of the final corrected-document Stage 0 run. There are five tasks and one output per task-condition cell; no error bars or population-level uncertainty claims are shown. The original benchmark is a separate anchor and is not part of the A/B comparison.

## Figures

1. Condition-level functionality and assigned-policy-and-functional performance.
2. Functionality and conditional policy behavior by information level.
3. Exact paired A-only to B-only controllability by task and condition.
4. Functional A-only/B-only/neither/both outcome composition.
5. Per-task functionality and assigned-policy heatmaps.
6. Automatic continuation-gate summary, with manual G7 noted separately.

Each figure is emitted as a 300-DPI PNG and an editable SVG. CSV files contain the plotted source values. `figure-manifest.json` binds every output to the source report.

Regenerate from the repository root with:

```bash
uv run --extra plots python scripts/plot_stage0_results.py
```
