# Stage 2 final figures

These figures summarize the finalized Stage-1-linked Stage 2 pilot artifacts. The local Qwen3.5-4B model passed the preregistered model-floor check, checkpoint 36 was selected using the one-task dev split, and final evaluation used the single held-out archive task.

## Figures

1. Key evidence: model floor, dev checkpoint selection, and held-out outcome summary.
2. QLoRA training and dev-loss dynamics.
3. Detailed behavioral comparison of the three dev checkpoints.
4. Held-out functionality, policy behavior, and mean plan length by condition.
5. Held-out functional policy-outcome composition.
6. Behavior-blinded plan audit and false-certificate rates.
7. Full-document versus planner-to-renderer bottleneck sanity check.

Each figure is emitted as a 300-DPI PNG and editable SVG. CSV files contain the plotted values, and `figure-manifest.json` records SHA-256 hashes for every source and output.

The test result is a one-task case study, not evidence of population-level generalization. A completed attempt that was truncated or otherwise unevaluable remains a model failure in unconditional denominators. No functional output passed both policy suites.

Regenerate from the repository root with:

```bash
uv run --extra plots python scripts/plot_stage2_results.py
```
