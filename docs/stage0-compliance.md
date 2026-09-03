# Stage 0 proposal-compliance sweep

This trace treats the attached experimental plan as a specification. It covers Stage 0 plus the
task, prompt, sandbox, and provenance constraints that Stage 0 depends on. Stages 1–4 and the GRPO
stretch goal are outside this checkpoint.

## Requirement trace

| Proposal requirement | Implementation status | Evidence |
| --- | --- | --- |
| Five candidate tasks | Implemented | Five task paths are schema-enforced in `config/stage0.toml`. |
| One legitimate A/B pair per task with the same surface request | Implemented; legitimacy remains a human judgment | Each task has one shared surface request and two explicit policy records. |
| Identical irrelevant clauses; only applicable value changes | Implemented | Schema and corpus audit reject changed distractors, clause IDs, or order. |
| Five or six clauses, approximately 150–250 tokens | Implemented | Schema requires 5–6 clauses; audit enforces the approximate-token range and a 25-token A/B tolerance. |
| Applicable position balanced | Implemented | The five tasks occupy positions 1, 2, 3, 4, and 5 exactly once. |
| A/B tests are mutually distinguishing | Implemented | Both references must pass functionality/security, pass their assigned suite, and fail the opposite suite. |
| Unmodified CWEval anchor | Implemented after sweep | Exact upstream code prompts are hash-checked and pinned to CWEval revision `e9a2a124c8c53679b6d8d27adfd2f6c40e7576d7`; faithful functionality/security test ports run separately from adapted A/B suites. |
| No assigned-value leakage from the surface request | Implemented with automated and prior human audit | Only the applicable document clause changes across A/B prompt pairs; labels and gold clause IDs are not sent. |
| Eight outputs per task | Implemented | The frozen matrix has 40 jobs across all eight required conditions. |
| Native-thinking ceiling | Implemented | Only the two native-thinking A/B conditions send `thinking.type=enabled`; reasoning and token usage are preserved separately. |
| Provider rate-limit recovery | Implemented | Request starts are spaced by 25 seconds. A retryable 429 requires a new lineage-linked manifest, a preserved prior-attempt hash, a 65-second cooldown, and one explicit manual retry authorization; automatic retries remain disabled. |
| Functionality, A, B, and security execution | Implemented | Adapted direct conditions run four fresh suites. Upstream anchor jobs run functionality/security and mark A/B not applicable. |
| Sandboxed generated-code execution | Implemented | Docker is the default, with no network, read-only mounts/root, dropped capabilities, resource limits, timeouts, and fresh state. |
| Continuation rules are not statistical claims | Implemented | Reports identify them as five-task engineering gates and never emit confidence claims. |
| Frozen prompts and decision rules | Implemented | Exact requests, upstream revisions/task IDs/prompt hashes, test-suite hashes, harness versions, model settings, internal pair IDs, sandbox settings, and thresholds are bound into immutable artifacts. |

Hosted Kimi does not document a provider-side seed parameter. Original-anchor and surface jobs
therefore record `pair_id: null`; each relevant-only, full-document, or native-thinking A/B pair
receives its own explicit non-seed `pair_id`. Every job records `provider_seed_supported: false`
and `provider_seed_sent: null`. Hosted A/B jobs are request-paired, not deterministic seed-matched;
mechanistic work must first reproduce the phenomenon on the local open-weight model, where actual
seed control can be applied.

## Continuation-rule interpretation

Policy-compliance gates are calculated among functionally correct outputs. This follows the
proposal's metric definition and prevents an otherwise broken implementation from passing a narrow
policy test. The report also retains raw policy pass rate and joint assigned-policy-plus-functional
rate for audit.

The proposal's Stage 0 criterion 7 says “full plans select the applicable clause,” but the eight
Stage 0 conditions generate code directly. G7 therefore audits the dataset instead: a reviewer
must verify one unambiguous applicable clause and genuinely irrelevant distractors in every safety
document. Model clause selection is deferred to Stage 1.

G5 and G8 use provisional 20% thresholds, corresponding to one of five tasks. G6 is instead a
zero-tolerance test-integrity check: any functional adapted output passing both policy suites marks
the result `invalid_task_or_tests`. G1b separately requires 40% full-document functionality.

## Deliberately out of scope

- Stage 1 planner-to-renderer plans, plan-length matching, clause-order and distractor controls.
- Structured/free-form, opposite-policy, wrong-clause, and shuffled-plan controls.
- Local-model SFT, activation capture, probes, causal interchange, and recurrent steering.
- Population-level uncertainty intervals; the proposal schedules those after prompt freezing on the
  complete development set.
- The separate activation-hook smoke-test utility listed in the time plan; it remains the next
  audited implementation checkpoint.

## Credential-day sequence

1. Start Docker and run `uv run sable-ir audit-tasks` without `--unsafe-local`.
2. Revoke any credential disclosed outside the shell, export a replacement `MOONSHOT_API_KEY`, and
   run `uv run sable-ir kimi-preflight`.
3. Run the targeted non-thinking upstream-anchor canary from the hosted-Kimi runbook.
4. Run the targeted native-thinking canary and confirm nonzero reasoning content/usage.
5. Evaluate both canaries in Docker and inspect their immutable artifacts.
6. Unlock the remaining jobs with the exact run-ID confirmation, then evaluate all 40.
7. Manually audit document applicability and distractor irrelevance, then record both results in a
   new final report ID.
