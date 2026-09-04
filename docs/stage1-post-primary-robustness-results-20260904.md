# Stage 1 post-primary robustness results

Status: **complete descriptive addendum**

The primary Stage 1 report remains frozen at `continue_to_stage2`; this addendum neither changes its gates nor strengthens its causal language. The 24 cells are the exact cells previously frozen for the wrong-clause sample. Clause order used one global reversal of all six clauses. Shuffled-task used the frozen no-fixed-point task mapping. Both conditions used one renderer output per cell, 25-second start-to-start pacing, fixed 4K renderer output limits, and no automatic retries.

## Results

### Clause order

The behavior-blinded plan audit found the applicable clause in 24/24 plans and the correct A/B distinction in 24/24. Rendering was stable relative to the same 24 natural `p00/r00` cells:

| Metric | Matched natural | Reversed clause order | Change |
| --- | ---: | ---: | ---: |
| Functional | 23/24 | 23/24 | 0.0 points |
| Assigned-policy pass | 21/24 | 21/24 | 0.0 points |
| Assigned-policy-and-functional | 20/24 | 21/24 | +4.2 points |

This is reassuring descriptive evidence that the planner's extraction was not fragile to the relevant clause's position in these sampled documents. Only 10/24 reordered plans happened to meet the earlier strict natural-plan length tolerance; exact plan-length matching was not preregistered for this positional robustness check. Format, nominal concision, request, policy, and clause text were fixed.

### Shuffled task

Grossly mismatching plan and request caused substantial disruption:

| Metric | Matched natural | Shuffled-task plan | Change |
| --- | ---: | ---: | ---: |
| Functional | 23/24 | 11/24 | -50.0 points |
| Assigned-policy pass | 21/24 | 7/24 | -58.3 points |
| Assigned-policy-and-functional | 20/24 | 6/24 | -58.3 points |

Three shuffled command-task outputs reached the fixed 4K ceiling. They remain model/functionality failures in the primary 24-row descriptive result, without replacement sampling. A post-outcome sensitivity that excludes all three still shows functionality falling from 20/21 to 11/21 and assigned-policy-and-functional falling from 17/21 to 6/21. The disruption therefore is not solely a truncation artifact.

Together, the controls show the reassuring opposing pattern specified before these outcomes: reordering irrelevant context did not materially change behavior, whereas replacing the plan with a different task's plan did. These are robustness observations only. They do not prove mediation, internal plan use, or any mechanism.

## Parser-only recovery

One clause-order planner response used whitespace-delimited inline labels (`SOURCE content`) rather than colon-delimited labels (`SOURCE: content`). The transmitted prompt required the six ordered labels but did not require colons. The original parser marked it malformed even though all six fields were present, ordered, nonempty, and followed by one terminal `END_PLAN`.

The parser was broadened to accept either delimiter while retaining all duplicate, missing, empty, ordering, and sentinel checks. A lineage-linked reparse reused the exact provider response plus its terminal newline. No semantic text was changed and no additional model call was made.

## Evidence hashes

| Artifact | SHA-256 |
| --- | --- |
| `artifacts/stage1/stage1-post-primary-robustness-selection-20260904.json` | `fe53b4dfb97f9ad4727c705ec66aa8b47b185b162a7bb0c122a4ee36ee6f243f` |
| `artifacts/stage1/audits/stage1-post-primary-design-preflight-20260904.json` | `1c404f365571a98fd0e6a367cf285bbf8e25b9fb5196d5d5cb8ee481925ae148` |
| `artifacts/stage1/audits/stage1-post-primary-parser-amendment-20260904.json` | `d155665c8d2e47d7225d36a087d3a99b302799d8c7102dc9391def4ccc3bb887` |
| `artifacts/stage1/stage1-control-plans-20260904-clause-reparse1/manifest.json` | `ae8dfc1579dfe4cb68dac95676119057c1f92086883660e2322ef7a19833d2b1` |
| `artifacts/stage1/stage1-control-plans-20260904-clause-reparse1/audits/clause-order-post-primary.completed.json` | `4123e2f2b70dcadb6daa7dc3587b9a0a856b5a4aca23736e4ac9dde894245333` |
| `artifacts/stage1/stage1-clause-order-post-primary-20260904/manifest.json` | `ce532367e85ca7fb6c301d6b5fb940340070fdaba7f987cff60fc8d94b64d461` |
| `artifacts/stage1/reports/stage1-clause-order-post-primary-behavior-20260904.json` | `ad54309b0248e3fdd4eae1e99b9394fd244b0689ec85abf93b1c6b2f47f56928` |
| `artifacts/stage1/stage1-shuffled-task-post-primary-20260904/manifest.json` | `04b15e0828e22834e4cf3f202bd3212def58c8e107cf23a0d6b762cf13f02087` |
| `artifacts/stage1/reports/stage1-shuffled-task-post-primary-behavior-20260904.json` | `ef5cc184970a9ae96633ad3a2b7c074072851b88ccf939b5b018d40dd392a450` |
| `artifacts/stage1/reports/stage1-robustness-addendum-20260904.json` | `07aef61953a6107863b8b49ed8d211e8521cb1773f4bea11949f6b29b0a22d7a` |
| `artifacts/stage1/audits/stage1-post-primary-shuffled-truncation-sensitivity-20260904.json` | `3cc9036a9fa5a51155d7f0a128fa40ed2cbae614a08037d4fd2bf7b08381d4f8` |

The completed total is 852 Stage 1 code outputs: 720 natural, 60 opposite-policy, 24 wrong-clause, 24 clause-order, and 24 shuffled-task.
