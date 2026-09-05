# Quarantined: aborted five-task floor run (2026-09-03)

Aborted at 168/1100 results after review found two experimental-separation defects:

1. It spanned all five tasks, so the held-out TEST task (path_symlink_archive) would have
   influenced the 4B-vs-9B model-floor recommendation.
2. It included the 180-plan / 720-render TRAINED-PLANNER matrix, which is a checkpoint-selection
   diagnostic, not model-floor evidence.

## Held-out task exposure — exact statement

An aborted implementation generated 36 pre-selection candidates for the held-out task
(path_symlink_archive): 36 plan.txt, 36 raw.txt, 36 result.json across 76 prepared job
directories. Neither their contents nor evaluation outcomes were inspected or used. They were
quarantined, and the corrected experimental chain permits no Stage 2 test generation until
checkpoint selection is frozen.

Verified facts supporting that statement:

- 0 evaluation.json files exist anywhere in this run: `evaluate-stage2-eval` was never invoked,
  so no sandbox/test outcomes were ever produced for any candidate, held-out or otherwise.
- 0 renderer candidates exist for the held-out task. The abort occurred during the plans phase;
  only planner text (plan.txt / raw.txt) was written, never rendered code.
- Only file counts and job-id prefixes were ever listed during triage. No result.json, plan.txt,
  raw.txt, or candidate file was opened, read, scored, or summarized.

If any candidate contents or test results are later found to have been inspected, the test is
compromised and must be described as a reused pilot case study. On the record above, nobody
inspected them, so the blinded test evaluation remains defensible.

These files MUST NOT be read, scored, or used as Stage 2 evidence.

## "Exactly once" means

Exactly one valid test_final run occurs after dev checkpoint selection is frozen. Stages 3 and 4
later reuse the same task for explicitly labelled mechanistic case studies, so the task is not
literally accessed only once across the project.

Replaced by a clean train+dev floor of 96 planner-independent jobs.
