# Stage 3: policy-orientation information tracing on the Windows RTX 5080 PC

Stage 3 records three aligned boundary states on the local Qwen3.5 planner and frozen renderer,
labels naturally generated plans for clause selection and visible policy retention, then uses
those labels plus the activations as a localization tool: an L2 logistic probe for the assigned
policy G, task-balanced difference-in-means directions, and the proposal's interpretation table.
Across unrelated vulnerability families these are **policy-orientation directions**. The only
fact-specific transfer claim available in this corpus is the symlink-policy transfer from
`path_symlink_report` to `path_symlink_archive`.
Nothing here is a causal claim. Held-out causal interchange is Stage 4 and is authorized only
when this report says `causal_evaluation_authorized`.

Everything below runs on the same Windows RTX 5080 (16 GiB) PC as Stage 2. Capture reuses the
Stage 2 extra (`torch` cu128, `transformers`, `peft`, `bitsandbytes`). Probe fitting is CPU-only
and uses the `stage3` extra (`numpy`, `scikit-learn`); that extra also installs on the Mac so
analysis can be checked without a GPU. Nothing in this track overwrites Stage 1 or Stage 2
artifacts.

## What is already frozen in the repository

| Artifact | Path | Role |
| --- | --- | --- |
| Config | `config/stage3.toml` | Layer schedule, 16-layer capture, paraphrase/audit/selection paths, probe C grid, direction alignment thresholds |
| Policy paraphrases | `data/stage3/policy-paraphrases.json` | Two disjoint sets × two framings (prohibition and permission) per task and policy |
| Paraphrase audit | `data/stage3/paraphrase-audit.json` | Meaning review of all 40 phrasings; flags start false |
| Labeling rubric | `data/stage3/labeling-rubric.json` | Family-specific rules for R and G labels, written before any plan is labeled |

The activation matrix is the Stage 2 3/1/1 split × 2 policies × 2 paraphrase sets × 2 phrasings
× 2 formats × 3 concision levels × 1 plan = **240 plans**, 3 renders each = **720 code samples**,
plus 2 surface-only renderer controls per task = **10**. Reports are labeled `pilot: true`. With
five tasks this is a mechanistic case study; the report's `generalization_claim` states that
explicitly (proposal XI.I.10).

Qwen3.5-4B has 32 decoder blocks (hidden size 2560). Capture records block outputs at every
fourth layer and every layer in a preregistered candidate region (14–24), which is 16 layers.
The capturer verifies both numbers against the loaded model. States are stored as float16
`.npy` files, hash-bound from the job result.

## PC setup

Same machine and checkout as [the Stage 2 runbook](stage2-planner-sft.md). Add the analysis extra:

```powershell
uv sync --extra dev --extra stage2 --extra stage3
```

Stage 3 will not freeze an activation run until Stage 2 has a passed model-floor report
(`continue_with_primary_model`) and a dev-selected adapter whose files still match
`artifacts/stage2/selection.json`. A `stop_or_pivot` floor is a planner/bottleneck finding and
does not authorize this track.

## Data track (no GPU)

1. Confirm the paraphrase file: both framings per policy per set, set 2 shares no six-word
   template with set 1, the frozen clause, or any Stage 2 training paraphrase.

   ```powershell
   uv run sable-ir validate-stage3-config
   ```

2. Meaning-review the 40 authored phrasings. The template is already at
   `data/stage3/paraphrase-audit.json`. For each row set `preserves_assigned_policy` and
   `framing_label_correct`, then fill `reviewer` and `completed_at`.

   ```powershell
   uv run sable-ir validate-stage3-paraphrase-audit
   ```

   Every plan detail in a phrasing must be the assigned A/B value in different wording, not a
   new requirement. Reviewing generated plans later does not replace this check.

## Capture (GPU)

```powershell
uv run sable-ir prepare-stage3-activations --run-id act-01
uv run sable-ir run-stage3-activations artifacts\stage3\activations\act-01\manifest.json
uv run sable-ir evaluate-stage3-activations artifacts\stage3\activations\act-01\manifest.json
```

`prepare` freezes every prompt, seed, layer list, adapter hash, model-floor recommendation, and
Stage 1/2 status before any forward pass. `run` is resumable (`--phase plans|renders|controls`,
`--limit N`). Plans use the Stage 2 adapter; renderer ingestion states and code generation run
inside `with model.disable_adapter():`. Sampling uses the same preregistered non-thinking
settings as Stage 2, with per-job fixed and recorded seeds.

The three states (proposal I.F):

- **planner input:** last prompt token before plan generation
- **planner output:** last token of `END_PLAN` after the generated plan, teacher-forced
- **renderer ingestion:** last token of `END_PLAN` after the renderer reads the plan, adapter off

`--dry-run` uses a stand-in capturer with random states; its outputs must never be reported.

The 4B forward pass at the Stage 2 sequence budget is expected to fit in 16 GiB. Peak memory is
not a new experiment; if capture OOMs, stop and record the failure rather than shrinking the
layer set after seeing results.

## Labels (no GPU)

Naturally generated compressed plans only. Do not delete fields to create a headline result.

```powershell
uv run sable-ir prepare-stage3-plan-audit artifacts\stage3\activations\act-01\manifest.json --output artifacts\stage3\activations\act-01\plan-audit.json
uv run sable-ir prepare-stage3-double-audit artifacts\stage3\activations\act-01\manifest.json --output artifacts\stage3\activations\act-01\plan-audit.double.json
```

Label from the plan text and the frozen task inputs using `labeling-rubric.json`. Never open
generated code, sandbox results, or `.npy` files. Set clause selection (correct / partially
correct / wrong clause / no applicable clause), policy visibility (preserved / omitted /
contradicted / ambiguous), selected and irrelevant clause ids, and confidence. The double packet
is every test-split plan plus a seeded 25% of train and dev. After both packets are complete:

```powershell
uv run sable-ir assemble-stage3-dataset artifacts\stage3\activations\act-01\manifest.json `
  --plan-audit artifacts\stage3\activations\act-01\plan-audit.json `
  --double-audit artifacts\stage3\activations\act-01\plan-audit.double.json `
  --output artifacts\stage3\activations\act-01\dataset.json
```

Assembly joins captures, sandbox outcomes, and both audits, assigns the four monitorability
quadrants (faithful success, false certificate, hidden use, visible omission with behavioral
failure), and reports Cohen's kappa. Kappa below 0.6 marks label reliability as below threshold.
Primary labels are used for analysis; disagreements are listed, not dropped.

## Analysis (CPU)

Two phases. Held-out base tasks and paraphrase set 2 are not touched during selection.

```powershell
uv run sable-ir fit-stage3-probes --dataset artifacts\stage3\activations\act-01\dataset.json --output-dir artifacts\stage3\analysis\fit-01
uv run sable-ir evaluate-stage3-heldout --selection artifacts\stage3\analysis\fit-01\selection.json --output artifacts\stage3\analysis\fit-01\heldout.json
uv run sable-ir report-stage3 --selection artifacts\stage3\analysis\fit-01\selection.json --heldout artifacts\stage3\analysis\fit-01\heldout.json --output artifacts\stage3\analysis\fit-01\report.json
```

`fit-stage3-probes` fits each probe from **all activation rows** in the training tasks / paraphrase
set 1. Sample weights give every base task equal total weight. The three task-level A/B difference
vectors are used only for direction estimation and alignment—not as the probe's three training
examples. C and layers are selected on development tasks. Reported uncertainty is clustered at
the base-task level; activation rows are never treated as independent evidence. The held-out
one-task result remains a case study, so its task-cluster interval is unavailable rather than a
spurious row-level interval.

The direction estimator averages task-level vectors with equal weight and freezes `selection.json`
plus every direction file. If renderer-ingestion task directions do not align, the report claims no
shared policy-orientation direction and does not authorize Stage 4 (VIII.E.7). The multiclass
clause-position probe is skipped in the five-task pilot (needs six training tasks).

Every activation, text, and metadata model uses the same C grid (VIII.F.12): TF-IDF, plan
length, TF-IDF plus length, applicable-clause position, clause length and position, irrelevant
clause identity, lexical framing, paraphrase-set identity, within-task shuffled labels, a
surface-only renderer control, and framing-transfer directions.

`evaluate-stage3-heldout` scores the frozen selection on held-out tasks and on paraphrase set 2.
A policy direction that works only on set 1 is a phrasing direction. Transfer to set 2 is
required before treating wG as the policy distinction.

The primary analysis is renderer ingestion restricted to plans labeled omitted or ambiguous
(reported as **blurred**), compared with surface-only and visible-text/length controls. Hidden-use
and false-certificate quadrants are reported separately. Each subset requires at least 10 rows and
both policy labels; otherwise its status is `insufficient_quadrant_support`. Pooled probe accuracy
is retained only as a localization diagnostic and is never substituted as the headline.

The report fills the interpretation table (VIII.G), records `stage1_gate` / `stage2_status` /
`stage3_status` by re-reading the Stage 1 report (provisional until Stage 1 passes; exploratory
if it fails), and sets:

- `probe_generalizes` only if renderer ingestion is held-out-decodable and transfers to set 2
- `causal_evaluation_authorized` only if renderer ingestion is decodable, transfers to set 2,
  renderer-ingestion task-level directions align, and the dataset is complete; planner-input and
  planner-output decoding localize loss but cannot unlock Stage 4
- `stop_or_pivot` quoting XIII.8 / VIII.H.4 / VIII.E.7 when those fail

Probe accuracy is a localization heuristic, not evidence that G is causally represented.

## Immutability

Every command writes new files only and refuses to overwrite. Config, paraphrases, split, Stage 2
adapter, model-floor report, and activation `.npy` files are bound by SHA-256. A changed input
aborts the consuming command. All JSON is written with LF newlines.
