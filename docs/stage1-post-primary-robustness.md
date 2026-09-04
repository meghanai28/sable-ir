# Stage 1 post-primary robustness addendum

This addendum was designed after the primary Stage 1 result was known. It is therefore descriptive and cannot alter the primary gate, the frozen `continue_to_stage2` decision, or the permitted causal language.

The frozen selection is `artifacts/stage1/stage1-post-primary-robustness-selection-20260904.json`. It reuses the exact 24 base cells selected for the wrong-clause control. This avoids an outcome-informed resample.

## Conditions

### Clause-order

For each selected cell, the implementation request, six clause texts, policy, plan format, concision, and decoding configuration are unchanged. The complete six-clause array is reversed with one deterministic global transformation. Kimi produces one new plan, that plan receives a behavior-blinded audit, and the renderer produces one code output.

The audit records whether the applicable clause was selected and whether the assigned A/B distinction survived. The behavioral report records functionality, assigned-policy compliance, assigned-policy-and-functional status, and paired differences from the matching natural `p00/r00` output.

### Shuffled-task

The target request, target A/B label, format, concision, and `p00` index are fixed. The renderer instead receives the natural plan from the following frozen derangement:

- `path_symlink_report` receives `path_symlink_archive`
- `path_symlink_archive` receives `sql_identifier`
- `sql_identifier` receives `command_executable`
- `command_executable` receives `ssrf_redirect`
- `ssrf_redirect` receives `path_symlink_report`

No task receives its own plan. The condition reports functionality, assigned-policy compliance, assigned-policy-and-functional status, and paired differences from the matching natural output. No exact reversal is expected or gated.

## Execution safety

- 24 clause-order planner calls, followed by 24 clause-order renders and 24 shuffled-task renders.
- One render per condition; cumulative Stage 1 code outputs become 852.
- Planner thinking ceiling remains 32K; renderer ceiling remains 4K.
- Start-to-start pacing remains at least 25 seconds.
- Automatic retries are disabled. Unexpected provider errors stop the current batch and preserve the attempt.
- A model-generated truncation or malformed program remains a model/functionality outcome; it is not replacement-sampled.

## Interpretation

High clause-order stability is reassuring evidence that extraction is not driven merely by clause position. Disruption under shuffled-task substitution is reassuring evidence that the renderer does not simply ignore grossly mismatched plan content. These are post-primary robustness observations, not new stop gates.

The canonical Stage 1 claim remains: **changing the visible plan while holding the coding request fixed can change implementation behavior.** The addendum cannot strengthen this into mediation, internal-use, or mechanistic language.
