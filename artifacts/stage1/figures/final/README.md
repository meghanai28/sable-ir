# Stage 1 final figures

These figures summarize the canonical Stage 1 v2 evidence packet (852 code outputs). The primary progression gate was frozen before its outcomes. Clause-order and shuffled-task controls were added after the primary result, but their design was frozen before their own outcomes; they remain supporting descriptive robustness evidence.

## Figures

1. Key evidence: exact opposite-policy reversal, clause-order stability, and wrong-task disruption.
2. Natural renderer performance across assigned policy, plan format, and requested length.
3. Exact opposite-policy reversals across all ten task-policy groups.
4. Exact visible-plan length distributions, including `END_PLAN`.
5. Natural assigned-policy-and-functional rates across the 60 design conditions.
6. Sampled wrong-clause negative control, with functionality reported separately.
7. Behavior-blinded plan audit and the supported scope of the compression analysis.

Each figure is emitted as a 300-DPI PNG and editable SVG. CSV files contain the plotted values. `figure-manifest.json` records SHA-256 hashes for every source and output.

The plots support behavioral claims only. They do not establish mediation or any internal mechanism. One supported length bin permits a format comparison, not a general compression trend or nonlinear/crossover claim.

Regenerate from the repository root with:

```bash
uv run --extra plots python scripts/plot_stage1_results.py
```
