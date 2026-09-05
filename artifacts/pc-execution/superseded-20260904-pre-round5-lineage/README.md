# Superseded: entire Stage 2 experimental chain, pre-round-5 (2026-09-04)

Rounds 4 and 5 corrected reference plans for sql_identifier and path_symlink_report (TRAIN) and
ssrf_redirect (DEV), which changed train.jsonl. Every artifact here was produced by an adapter
optimized toward SFT targets that have since been withdrawn, so none of it is usable evidence:

  training/sft-01      checkpoints 18/36/54, trained on superseded targets
  eval/floor-01        model floor (its reference-plan arm used superseded plans)
  eval/dev-18|36|54    checkpoint selection sweeps
  eval/dev-18-lowconcision
  selection.json       froze checkpoint-18 on superseded dev plans

The full-document direct floor arm (0.4375) never consumes reference or generated plans and is
the one number here that remains methodologically valid, though it is superseded operationally.

Run IDs are reused by the round-5 rerun so config paths stay stable. Do not compare the rerun
against these as if they were two experimental runs: this is an invalidated lineage, not a replicate.
