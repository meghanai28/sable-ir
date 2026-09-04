#!/bin/zsh
set -euo pipefail

readonly repository_root="${0:A:h:h}"
readonly control_manifest="artifacts/stage1/stage1-control-plans-20260904-lengthfix9/manifest.json"
readonly wrong_audit="artifacts/stage1/stage1-control-plans-20260904-lengthfix9/audits/wrong-clause-lean-v2.completed.json"
readonly selection="artifacts/stage1/stage1-lean-control-selection-20260904-v2.json"
readonly output="artifacts/stage1/reports/stage1-report-lean-for-review-v2-20260904.json"

cd "$repository_root"

uv run sable-ir validate-stage1-control-audit "$wrong_audit" "$control_manifest"

set +e
uv run sable-ir report-stage1 \
  --stage0-report artifacts/stage0/stage0-smoke-20260902-timeout-recovery/reports/final/stage0-report.json \
  --natural-behavior artifacts/stage1/reports/stage1-natural-behavior-20260904.json \
  --opposite-behavior artifacts/stage1/reports/stage1-opposite-lean-behavior-20260904.json \
  --wrong-clause-behavior artifacts/stage1/reports/stage1-wrong-clause-lean-behavior-20260904.json \
  --length-report artifacts/stage1/stage1a-plans-20260903-recovery3/analysis/stage1b-lengths.json \
  --plan-audit artifacts/stage1/stage1a-plans-20260903-recovery3/audits/stage1c-plan-audit.completed.json \
  --wrong-clause-control-audit "$wrong_audit" \
  --control-plan-manifest "$control_manifest" --lean-selection "$selection" \
  --output "$output"
report_status=$?
set -e
if [[ $report_status -ne 1 ]]; then
  print -u2 "unexpected Stage 1 report exit status: $report_status"
  exit 1
fi

jq -e '
  .design_variant == "lean_control_screen"
  and .dataset_and_plan_audits_passed == false
  and .recommendation != "continue_to_stage2"
  and ([.gates[].status] | all(. != "not_evaluable" and . != "invalid"))
' "$output" >/dev/null

print "STAGE1_REVIEW_REPORT_READY: $output"
