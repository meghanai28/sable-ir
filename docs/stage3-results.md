# Stage 3 results: no robust policy representation at the renderer boundary

**Preregistered gate failed. Stage 4 was not run.**

Run `act-01` / `fit-01` · Qwen3.5-4B, checkpoint-36 · five-task pilot · 240 plans, 720 renders
`stage1_gate: passed` · `stage2_status: valid_continuation` · `stage3_status: valid_continuation`

```
causal_evaluation_authorized : false
probe_generalizes            : false
```

> policy is not decodable at renderer ingestion on at least 10 held-out omitted/blurred plans
> containing both policy labels; pooled and planner-boundary decoding are localization evidence
> only and cannot authorize Stage 4

Because renderer-ingestion decoding failed the prespecified paraphrase-transfer criterion, we did
not perform causal interventions. Stage 4 was not run, and Stage 5 is blocked behind it.

---

## 1. The precise negative claim

The claim is **not** that nothing decodes. Weak signal exists on paraphrase set 1. What fails is
generalization to independently worded set 2, most severely at the renderer boundary — and, more
damagingly, the activations lose to a trivial text baseline.

| Boundary state | Layer | Held-out AUROC | Set 2 AUROC | Best text baseline | Decodable |
|---|---:|---:|---:|---:|---|
| `planner_input` | 16 | 0.627 | **0.535** | 0.813 | false |
| `planner_output` | 22 | 0.582 | **0.521** | 0.813 | false |
| `renderer_ingestion` | 14 | 0.578 | **0.493** | 0.813 | false |

### Task-clustered bootstrap intervals

| Evaluation | AUROC | 95% CI (task-clustered) | Reading |
|---|---:|---:|---|
| set 1 held out | 0.689 | [0.639, 0.750] | above chance |
| set 2 held out | 0.569 | [0.493, 0.604] | **straddles 0.5** |

> **State the negative this way.** There is *weak localization evidence* on paraphrase set 1 —
> planner input 0.627, planner output 0.582, renderer ingestion 0.578 on ordinary held-out test
> rows. What fails is *robust generalization to paraphrase set 2*, whose task-clustered interval
> includes chance. **Do not write "nothing decodes."** The numbers do not support that.

### The sharpest result: activations lose to reading the plan

On the preregistered headline subset — 23 held-out omitted/blurred plans containing both policies —
a trivial surface feature of the plan text outperforms the activation probe by a wide margin.

| Headline subset | Rows | Activation AUROC | Text baseline | Baseline used | Activation − text |
|---|---:|---:|---:|---|---:|
| omitted / blurred | 23 | **0.485** | 0.871 | `clause_length_and_position` | **−0.386** |
| false certificate | 18 | 0.675 | 0.805 | `tfidf` | −0.130 |
| hidden use | 6 | — | — | `insufficient_quadrant_support` (<10 rows) | — |

This is the strongest form of the negative. Activations do not merely fail to decode the policy; on
the subset the design nominated as its headline, they carry *less* policy information than clause
length and position — a feature obtainable by reading the plan without a model at all.
Activation-over-text gain is negative at every state.

---

## 2. What survives

The behavioural phenomenon did not disappear. What died is specifically *transferable linear A/B
representation → causal steering*, not *compressed plans have monitorability problems*.

| Monitorability quadrant | Rows | Meaning |
|---|---:|---|
| `faithful_success` | 105 | plan states the policy, behaviour follows it |
| `false_certificate` | **68** | plan states the policy, behaviour does not follow it |
| `hidden_use` | 14 | plan omits the policy, behaviour follows it anyway |
| `visible_omission_behavioral_failure` | 53 | plan omits the policy, behaviour fails it |

Visible retention 0.721 · clause selection correct 0.683 · confident-wrong-clause 0.033.

Sixty-eight false certificates on 240 plans is the monitorability gap stated directly: a
human-readable plan can assert the governing rule while the code beneath it does something else.

> **The combined result.** A human-readable intermediate plan can appear to expose the relevant
> decision without being a reliable certificate of downstream behaviour — while the downstream model
> also offers no obvious simple internal policy variable that would rescue monitoring.

### Label reliability

Two independent behavior-blind raters, one human and one clean-context AI, on 96 overlapping rows.
The double packet was shuffled with opaque row ids; assembly refuses to compute agreement when both
packets name the same reviewer.

| Measure | Agreement | Cohen's κ | Threshold 0.6 |
|---|---:|---:|---|
| clause selection | 0.875 | 0.788 | reliable |
| policy visibility | 0.833 | 0.714 | reliable |

Disagreements are not diffuse. Two tasks agree perfectly; 9 of 16 visibility disagreements are the
single pair `preserved → ambiguous`, concentrated in `path_symlink_archive`, where the stricter
reading requires a plan to address *both* symbolic and hard links before counting as preserved. The
rubric is well operationalized except at that one boundary.

---

## 3. Postmortem diagnostics

Three bounded analyses run **after** the gate returned false, using data already collected. They are
exploratory. None reopens the gate, and none can authorize Stage 4.

### 3.1 The null is not caused by one bad task

Per-task set-2 decoding, training on the other four tasks:

| Task | Set 2 AUROC | n | |
|---|---:|---:|---|
| `command_executable` | **0.250** | 24 | below chance |
| `path_symlink_archive` | 0.493 | 24 | at chance |
| `sql_identifier` | 0.563 | 24 | |
| `ssrf_redirect` | 0.604 | 24 | second best |
| `path_symlink_report` | 0.611 | 24 | best |

`ssrf_redirect` was the prime suspect — it carries a clause-driven credential confound and the
weakest labelling agreement. It is **second best**. Removing it would not rescue the result. The
worst task is `command_executable` at 0.250, which is anti-correlated. The null is broad, not local.

> **Caveat on leave-one-out.** Dropping a task appears to raise set-2 AUROC (0.569 → 0.62–0.83), but
> leave-one-out removes the task from the *evaluation* set as well as from training, so the apparent
> gain is confounded with evaluating on fewer tasks. The per-task table above is the honest view and
> the one to cite.

### 3.2 Decoding split by monitorability quadrant

Set-2 renderer-ingestion AUROC within each quadrant: faithful success 0.822, false certificate
0.879, visible omission 0.699, hidden use 0.630 — all above the pooled 0.569.

> **Why this is not a rescued signal.** Quadrant membership is defined partly from behavioural
> outcomes (functional rate, assigned-policy pass). Conditioning on it while predicting policy from
> activations is post-treatment conditioning on a collider. These numbers measure decodability
> *given the outcome*, not decodability, and cannot be used to argue the policy is decodable after
> all.
>
> The likely mechanism is visible in the balance: `hidden_use` skews B (9 of 12) and
> `visible_omission` skews A (19 of 30) — opposite directions — while the two large quadrants are
> balanced. A quadrant-dependent score offset destroys the pooled ranking while leaving
> within-quadrant ranking intact. That is Simpson's paradox, not recovered signal.
>
> It remains the most interesting exploratory thread available, but it needs a preregistered design
> rather than a post-hoc slice.

### 3.3 The null survives the second rater

On the 96 double-labelled rows, restricted to blurred plans in paraphrase set 2:

| Label source | Blurred rows | Set-2 blurred n | AUROC |
|---|---:|---:|---:|
| primary rater | 31 | 22 | 0.483 |
| independent second rater | 33 | 22 | 0.402 |

Both below chance. The stricter second-rater reading makes the result slightly *worse*, not better.
The negative is therefore not an obvious artifact of plan-label noise.

---

## 4. What was deliberately not done

After the gate failed, no search was performed over analysis choices. Each of the following is
legitimate future work and was excluded here because doing it now would convert a clean
preregistered negative into researcher degrees of freedom.

- No nonlinear probes, and no sparse-autoencoder or nonlinear-CAV features
- No search over layers until one worked — the reported layers came from dev selection before the
  held-out evaluation
- No alternative pooling strategies
- No change to the paraphrase sets
- No relaxation of the gate threshold
- No intervention run anyway

---

## 5. Scope and limitations

- **Five-task pilot.** One held-out base task (`path_symlink_archive`). The report records
  `generalization_claim: none` — fewer than twelve policy-counterfactual tasks.
- **Model-specific.** Results apply only to the pinned local Qwen3.5-4B and this
  adapter/base-renderer pairing. Hosted-model evidence is not mechanistic evidence for this model.
- **Small subsets.** The headline subset is 23 rows from a single task cluster, so the report
  records no task-clustered interval for it rather than manufacturing one. `hidden_use` at 6 rows is
  marked `insufficient_quadrant_support`.
- **A known confound, recorded not fixed.** Policy B's SSRF plan retains credential validation
  because clause B names it and clause A does not. Clause-driven rather than authored, but it leaves
  "credentials" as a non-policy lexical cue separating A from B.
- **Compression was weak.** Plan tokens moved only 154 → 131 across full/concise/minimal, so the
  concision manipulation did not produce a genuine compression frontier.
- **Negative result, not absence of effect.** Failure of a linear probe under paraphrase transfer
  does not establish that no policy representation exists.

---

## Reproduction

Preregistered thresholds: decodable AUROC ≥ 0.75, activation-over-text gain ≥ 0.05, minimum 10 rows
per subset with both policy labels, κ ≥ 0.6. Probe layers and C values were selected on development
tasks and frozen before held-out evaluation.

Artifacts (untracked, produced by the run):

```
artifacts/stage3/activations/act-01/dataset.json
artifacts/stage3/analysis/fit-01/{selection,heldout,report}.json
artifacts/stage3/analysis/fit-01/POSTMORTEM-DIAGNOSTICS.txt
```

Every input is SHA-256 bound. `uv run sable-ir verify-audit-packet` recomputes the 20-plan → 240-row
expansion, re-hashes all audit rows, checks the dataset counts and file hashes, and re-derives
training, selection and evaluation lineage from repository bytes, exiting non-zero on any
disagreement.
