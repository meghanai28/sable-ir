#!/bin/zsh
set -euo pipefail

readonly repository_root="${0:A:h:h}"
readonly control_manifest="artifacts/stage1/stage1-control-plans-20260903/manifest.json"
readonly wrong_audit="artifacts/stage1/stage1-control-plans-20260903/audits/wrong-clause.completed.json"
readonly order_audit="artifacts/stage1/stage1-control-plans-20260903/audits/clause-order.completed.json"
readonly output="artifacts/stage1/reports/stage1-report.for-review.json"

cd "$repository_root"

uv run sable-ir validate-stage1-control-audit "$wrong_audit" "$control_manifest"
uv run sable-ir validate-stage1-control-audit "$order_audit" "$control_manifest"

uv run sable-ir report-stage1 \
  --stage0-report artifacts/stage0/stage0-smoke-20260902-timeout-recovery/reports/final/stage0-report.json \
  --natural-behavior artifacts/stage1/reports/natural-behavior.json \
  --opposite-behavior artifacts/stage1/reports/opposite-behavior.json \
  --shuffled-behavior artifacts/stage1/reports/shuffled-behavior.json \
  --wrong-clause-behavior artifacts/stage1/reports/wrong-clause-behavior.json \
  --length-report artifacts/stage1/stage1a-plans-20260903-recovery3/analysis/stage1b-lengths.json \
  --plan-audit artifacts/stage1/stage1a-plans-20260903-recovery3/audits/stage1c-plan-audit.completed.json \
  --wrong-clause-control-audit "$wrong_audit" \
  --clause-order-control-audit "$order_audit" \
  --control-plan-manifest "$control_manifest" \
  --output "$output" || [[ "$?" == "1" ]]

jq -e '
  .dataset_and_plan_audits_passed == false
  and .recommendation != "continue_to_stage2"
  and ([.gates[].status] | all(. != "not_evaluable" and . != "invalid"))
' "$output" >/dev/null

print "STAGE1_REVIEW_REPORT_READY: $output"
