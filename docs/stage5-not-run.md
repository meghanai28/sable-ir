# Stage 5 was not run

Stage 5 is analysis-only and requires complete Stage 1–4 reports at the exact paths in
[config/stage5.toml](../config/stage5.toml). Stage 4 was never executed, because the preregistered
Stage 3 gate returned `causal_evaluation_authorized: false` (see
[the Stage 3 results report](stage3-results.md)). Stage 5 therefore has no qualifying inputs.

## The exact blocker

```
$ uv run sable-ir prepare-stage5-inputs --run-id analysis-01 \
    --output artifacts/stage5/analysis-01/input-manifest.json

prior-stage artifacts are missing: stage4_full_manifest, stage4_report
```

Missing paths, both of which only a completed Stage 4 produces:

```
artifacts/stage4/full/heldout-01/manifest.json
artifacts/stage4/full/heldout-01/report.json
```

`src/sable_ir/stage5.py` loads `Stage4FullRunManifest` and `Stage4Report` unconditionally, builds
`_stage4_rows` from them, and hashes the Stage 4 report into the input manifest. There is no
partial-input mode, by design.

## Why this is not just a missing section

Stage 5's ambiguity floor requires at least eight functional, A-or-B-classifiable outputs per
exact plan. Stage 4's full run is the only source in the whole design that supplies enough renderer
draws to clear it: it produces 16 samples per condition, whereas Stage 1–3 plans typically have
fewer than eight draws each and are explicitly retained as **excluded diagnostics** rather than
promoted when Stage 4 is absent.

So without Stage 4, Stage 5's ambiguity analysis and its policy-collision indexing have no
qualifying rows at all — not a reduced sample, an empty one.

## What Stage 5 would have added, and what already covers it

| Stage 5 output | Status |
| --- | --- |
| Visible assigned-policy retention | **Already reported.** 0.721 across 240 Stage 3 plans; per-cell values in the Stage 2 held-out report |
| False certificates | **Already reported.** 68 of 240 at Stage 3; per format × concision on the held-out task at Stage 2 |
| Assigned behaviour under invisible policy (hidden use) | **Already reported.** 14 of 240 |
| Visible-plan policy failures | **Already reported.** 53 of 240 |
| Functionality, assigned-and-functional, opposite-policy, original-security | **Already reported** in the Stage 2 floor, dev and held-out test reports |
| Clause-selection precision, irrelevant-clause inclusion, confident-wrong-clause | **Already reported.** Correct-clause 0.683, confident-wrong 0.033 |
| Plan-length curves for retention, policy behaviour, functionality | **Partially covered.** Stage 2 held-out report has the format × concision curve, but the compression manipulation was weak (plan tokens 154 → 131), so the frontier spans little range |
| HU+ separately for A and B, task-balanced | **Not usable.** On the held-out task the surface-only baseline for policy B saturates at 1.0 off n=4, making HU+ B = −1.0. Both HU+ values should be reported as `insufficient_support`, not as measurements |
| Exact-plan A/B collision index, qA, AAB, ambiguity floor | **Lost.** Requires Stage 4's 16-draw conditions; cannot be reconstructed from Stages 1–3 |
| Frozen collision taxonomy and held-out vocabulary coverage | **Lost.** Depends on the collision index above |
| Hosted-Kimi versus local-Qwen stratified comparison | **Lost.** The stratified tables are produced by the Stage 5 pipeline only |

The monitorability *phenomenon* Stage 5 was built to quantify is therefore documented; what is
genuinely unavailable is the **policy-collision taxonomy** and the stratified cross-model tables.

## What was deliberately not done

Stage 5 could have been made to emit a partial report by relaxing its Stage 4 requirement. That was
rejected for the same reason no post-hoc probe search was run after the Stage 3 gate failed: it
would be a code change made *after* seeing a negative result, in order to extract a number the
design states is unsupported. The ambiguity floor would fail regardless.

Specifically, none of the following were done:

- No editing of `stage5.py` to make Stage 4 inputs optional
- No substitution of Stage 1–3 renderer draws for Stage 4's 16-sample conditions
- No lowering of the eight-output ambiguity floor
- No reporting of collision rates from an empty or under-supported index

## Terminal state of the pipeline

| Stage | Question | Outcome |
| --- | --- | --- |
| 0 | Is the policy behaviourally real? | Yes |
| 1 | Does it cross a visible planner → renderer bottleneck? | Yes — `continue_to_stage2` |
| 2 | Can this be reproduced locally, with monitorability failures observable? | Yes, with limitations — floor `continue_with_primary_model`, 68 false certificates |
| 3 | Is there a paraphrase-robust internal A/B representation supporting intervention? | **No**, under the tested linear-probe protocol |
| 4 | Causal intervention | **Not run** — the preregistered Stage 3 gate failed |
| 5 | Downstream monitorability and policy-collision analysis | **Not run** — requires a complete Stage 4 report |

For a paper, the sentence is:

> Because renderer-ingestion decoding failed the prespecified paraphrase-transfer criterion, we did
> not perform causal interventions, and the downstream collision analysis that depends on them was
> not run.
