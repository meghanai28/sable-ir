# Quarantined: aborted test-01 (2026-09-04)

Aborted at 164/204 generations when sign-off review round 4 corrected sql_identifier and
path_symlink_report (TRAIN) and ssrf_redirect (DEV). Those corrections changed train.jsonl, so
checkpoint-18 -- the adapter this run used -- was trained on superseded SFT targets, specifically
the invented requirements ("bind limit as a query parameter", "reject absolute filenames") that
the review removed.

Held-out task exposure, exact statement:

An aborted implementation generated 164 pre-selection candidates for the held-out task
(path_symlink_archive) using an adapter later invalidated. ZERO evaluation.json files exist in
this run: evaluate-stage2-eval was never invoked, so no sandbox or test outcomes were ever
produced for any of them. Neither their contents nor any outcome were inspected or used. Only
file counts and job-id prefixes were listed during triage.

These files MUST NOT be read, scored, or used as Stage 2 evidence. A valid test_final run occurs
only after retraining on the corrected dataset and re-freezing checkpoint selection.
