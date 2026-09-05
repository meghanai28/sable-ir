# Superseded: path_symlink_archive content, v3 (2026-09-04)

Content review returned FAIL for path_symlink_archive. Five defects, all now corrected:

1. MAJOR containment guard covered only "every regular file and directory", narrower than the
   surface requirement that NO member be written outside dest_path. Under B an escaping link
   NAME with a contained target was uncovered; non-link special members uncovered under both.
   Now: normalize EVERY member's extraction path, then apply the A/B link-target rule separately.
2. MAJOR policy A was strengthened from member rejection to WHOLE-ARCHIVE rejection. The clause
   says reject every link member and that regular files/directories may still be extracted. The
   whole-archive reading came from policies.A.required_behavior -- EVALUATION METADATA that the
   planner prompt never contains (build_stage2_planner_prompt takes only surface_request and the
   rendered clauses). This was a hidden-information leak of exactly the kind the
   inferable_from_visible_inputs_only flag exists to catch.
3. MAJOR special-entry removal was incomplete: "only regular files and directories may be
   extracted" survived in the policy-A paraphrase and Stage 3 phrasings, banning FIFO/device
   entries that clause A is silent about.
4. MODERATE policy A imported policy B's explicit global preflight ("inspect every member before
   extracting anything" / "validate the complete member list first"). Stated only in clause B.
5. LOW unsupported "then create dest_path" ordering; the visible request never says the
   destination is absent.

Impact: path_symlink_archive is the TEST split task, so train.jsonl is unchanged and NO
RETRAINING is required. The model floor used reference plans for train+dev only, so the floor
verdict is unaffected. Dev selection used the dev task only. test-01 generates plans from the
model and does not read reference plans.
