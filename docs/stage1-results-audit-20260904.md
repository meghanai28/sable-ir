# Stage 1 lean-design results audit

Status: **experimentally complete; manual review required**

This packet records the lean Stage 1 amendment and the completed behavioral results. It is intentionally not the canonical `continue_to_stage2` report: the automatic checks pass, but the final dataset/plan-review flag remains false until a human approves this packet.

## Frozen design

The lean amendment keeps the central paired intervention and reduces secondary controls:

| Condition | Frozen sample | Role |
| --- | ---: | --- |
| Natural planner/renderer | 720 evaluated render rows | Main Stage 1 factorial experiment |
| Opposite-policy render | 60, one for every task × policy × format × concision cell | Primary paired intervention |
| Wrong-clause planner/render | 24 behavior-blinded, semantically screened samples, one render each | Sampled descriptive negative control |
| Clause-order | 0 | Omitted noncentral robustness check |
| Shuffled-task | 0 | Omitted redundant sanity check |

The 24 wrong-clause plans cover every task, both policies, both formats, and all three concision levels. They are balanced 12/12 across A/B; task counts are 7/4/4/4/5 and format counts are 13/11. Six initially selected or replacement candidates failed the behavior-blinded semantic screen and were excluded before rendering. Their exclusions and replacements remain in the audit artifacts.

The lean primary gate uses at least 40 jointly functional pairs spanning all ten task-policy groups. This is a deliberate amendment to the earlier 60-eligible-pair floor: after reducing the experiment to 60 total one-shot conditions, requiring 60 jointly functional outputs would make any single model functionality failure automatically erase the primary result. The achieved denominator is 57 and coverage is 10/10 groups. A reviewer who does not approve this threshold amendment should classify the result as `insufficient_control_support` under the former rule, rather than reinterpret the data.

## Results

- Natural outputs: 720/720 evaluated; functionality 679/720 (94.3%); assigned-policy-and-functional 639/720 (88.8%); policy controllability 79.7%; mutually-exclusive-suite violations 0.
- Primary opposite-policy intervention: 60/60 evaluated; 59/60 functional. Among 57 pairs where both natural and controlled outputs were functional, 50 showed the exact assigned-only → opposite-only reversal (87.7%). Eligible pairs span all 10 task-policy groups. Gate S1.2 passes the frozen lean threshold of 20% with at least 40 eligible pairs.
- Sampled wrong-clause control: 24/24 evaluated. Matched functionality fell from 23/24 natural (95.8%) to 15/24 controlled (62.5%). Among the 15 jointly functional pairs, assigned-policy passes fell from 12/15 to 5/15, a descriptive 46.7-point drop, with coverage across 7 task-policy groups. This is not a stop gate and does not inherit the primary intervention's denominator floor.
- Length analysis: one supported strict-match bin has 13 pairs spanning 8 task-policy groups. This supports a format comparison only; it does not support a compression trend or nonlinear/crossover claim.
- Plan visibility: the hosted Kimi sample retained explicit policy content in 100% of audited plans. Stage 1 therefore provides behavioral plan-dependence evidence, but no hosted-model natural hidden-use result.

Three wrong-clause renderer outputs reached the fixed 4K output ceiling and ended with malformed code. They are preserved as one-shot model/functionality failures, not infrastructure errors. One separately lineage-linked same-ceiling sensitivity retry also truncated and is excluded from the primary 24-row analysis. No automatic retries or outcome-conditioned replacements were used.

## Interpretation boundary

The supported Stage 1 claim is: **changing the visible plan while holding the coding request fixed can change implementation behavior.** The evidence is the exact paired reversal under opposite-policy plan substitution. The wrong-clause result is secondary and descriptive. Clause-order robustness and shuffled-task behavior were not tested in the lean amendment.

These are behavioral results for hosted `kimi-k2.6`. They do not establish a mechanism in the later local open-weight model. Stage 3/4 mechanistic and causal claims remain model-specific and subject to their own authorization gates.

## Immutable evidence

| Artifact | SHA-256 |
| --- | --- |
| `artifacts/stage1/reports/stage1-natural-behavior-20260904.json` | `07de8f87bb3a9cf069f9f06791d2f1c3286cbdd7df8e34e9987144ad29649ba5` |
| `artifacts/stage1/reports/stage1-opposite-lean-behavior-20260904.json` | `565df9dfeca35fda5d94d510f203c9ffbfb4a66487883f9cccc9c88ab899cc57` |
| `artifacts/stage1/reports/stage1-wrong-clause-lean-behavior-20260904.json` | `1377c3308a19e56ca1e91d94b28cfe4f62d2d78b56739150267e0947169cc63e` |
| `artifacts/stage1/reports/stage1-report-lean-for-review-v2-20260904.json` | `497ef5aef2509dc8ca4c9559b53ac3ba9f4681054075bdbe6d17c4340865d42b` |
| `artifacts/stage1/stage1-lean-control-selection-20260904-v2.json` | `0b4b4c1f75b37dc54273cdf4e5b3e8834980a7535b9eb9bc98697657e0b6c3df` |
| `artifacts/stage1/stage1-opposite-lean-20260904-v2/manifest.json` | `2699504dd155a9564cf81be54585c4e45b259d03ee20f63232adf8ce013cdc75` |
| `artifacts/stage1/stage1-wrong-clause-lean-20260904-v2/manifest.json` | `ad77b704cc4273e2208f63aa464d4e89000ea4c36943e4dcd8513cb5787c3989` |
| `artifacts/stage1/stage1-control-plans-20260904-lengthfix9/audits/wrong-clause-lean-v2.completed.json` | `dfc2bd1de4fd5797e67ef5006bcb8e1bce4f5ca60e7144ca27bcbf1f365181e3` |
| `artifacts/stage1/audits/stage1-lean-control-semantic-screen-v1-20260904.json` | `c7b8c580c4b9650961d5c9d2431316b4f3a340fc2e2d555a12546be779b8c067` |
| `artifacts/stage1/audits/stage1-lean-control-semantic-repair-screen-20260904.json` | `1a84ace1a42825e81cffcab7c3ccf77783b38de84ab5b35f56c527a69697e4f2` |
| `artifacts/stage1/audits/stage1-lean-wrong-clause-truncations-20260904.json` | `0193bdccf46d00366ae6155672f1353b4128a449fcd300ef1148f5bba6d94bb1` |

## Review decision

Approve only if all of the following are acceptable:

1. The lean primary support floor is 40 jointly functional pairs rather than the earlier 60, with the observed result 50/57 across all ten groups.
2. The three wrong-clause truncations count as model failures and the excluded retry is sensitivity-only.
3. Wrong-clause is a sampled descriptive control, not a causal stop gate.
4. No clause-order or shuffled-task claim is made.
5. One supported length bin permits format comparison only.

On approval, regenerate the canonical Stage 1 report with the manual-review flag. Until then, `manual_review_required` is the correct terminal state.
