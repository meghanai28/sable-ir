#!/bin/zsh
set -euo pipefail

readonly repository_root="${0:A:h:h}"
readonly plan_manifest="artifacts/stage1/stage1a-plans-20260903-recovery3/manifest.json"
readonly plan_audit="artifacts/stage1/stage1a-plans-20260903-recovery3/audits/stage1c-plan-audit.completed.json"
readonly natural_manifest="artifacts/stage1/stage1a-renders-20260903-recovery3/manifest.json"
readonly surface_report="artifacts/stage1/stage1-surface-20260903/report.json"
readonly control_plan_manifest="artifacts/stage1/stage1-control-plans-20260903/manifest.json"
readonly wrong_audit="artifacts/stage1/stage1-control-plans-20260903/audits/wrong-clause.completed.json"
readonly wrong_manifest="artifacts/stage1/stage1-wrong-clause-20260903/manifest.json"
readonly stage0_report="artifacts/stage0/stage0-smoke-20260902-timeout-recovery/reports/final/stage0-report.json"
readonly tokenizer="artifacts/stage1/tokenizers/kimi-k2.6-7eb5002f.tiktoken.model"

cd "$repository_root"
set -a
source .env.stage0.local
set +a

mkdir -p artifacts/stage1/reports

if [[ ! -f artifacts/stage1/reports/natural-behavior.json ]]; then
  uv run sable-ir report-stage1-behavior "$natural_manifest" "$plan_manifest" \
    "$plan_audit" "$surface_report" "$stage0_report" \
    --output artifacts/stage1/reports/natural-behavior.json
fi

if [[ ! -f "$wrong_manifest" ]]; then
  uv run sable-ir prepare-stage1-render-control "$plan_manifest" --kind wrong_clause \
    --control-plan-manifest "$control_plan_manifest" --control-plan-audit "$wrong_audit" \
    --run-id stage1-wrong-clause-20260903 \
    --run-directory artifacts/stage1/stage1-wrong-clause-20260903
fi

function run_renderer_control() {
  local kind="$1"
  local run_id="$2"
  local manifest="$3"
  local behavior_output="$4"
  local canary
  canary="$(jq -r '.jobs[0].job_id' "$manifest")"
  print "starting ${kind} renderer control"

  uv run sable-ir generate-stage1-renders "$manifest" --job-id "$canary"
  uv run sable-ir evaluate-stage1-renders "$manifest" --job-id "$canary"
  uv run sable-ir generate-stage1-renders "$manifest" --all --confirm-full-run "$run_id"
  uv run sable-ir status-stage1a "$plan_manifest" --render-manifest "$manifest" \
    | jq -e '.pending_renders == 0' >/dev/null
  uv run sable-ir evaluate-stage1-renders "$manifest"
  uv run sable-ir report-stage1-behavior "$manifest" "$plan_manifest" "$plan_audit" \
    "$surface_report" "$stage0_report" --output "$behavior_output"
}

run_renderer_control opposite_policy stage1-opposite-20260903 \
  artifacts/stage1/stage1-opposite-20260903/manifest.json \
  artifacts/stage1/reports/opposite-behavior.json
run_renderer_control wrong_clause stage1-wrong-clause-20260903 \
  "$wrong_manifest" artifacts/stage1/reports/wrong-clause-behavior.json
run_renderer_control shuffled_task stage1-shuffled-20260903 \
  artifacts/stage1/stage1-shuffled-20260903/manifest.json \
  artifacts/stage1/reports/shuffled-behavior.json

# Reversed document order is intentionally last and is used only for its selection audit.
readonly order_canary="command_executable__plan_a__freeform__concise__p00__control_clause_order"
uv run sable-ir generate-stage1-control-plans "$control_plan_manifest" \
  --kind clause_order --job-id "$order_canary"
uv run sable-ir generate-stage1-control-plans "$control_plan_manifest" \
  --kind clause_order --all --confirm-full-run stage1-control-plans-20260903

readonly all_control_plan_results="$(find artifacts/stage1/stage1-control-plans-20260903/jobs \
  -name result.json -type f | wc -l | tr -d ' ')"
[[ "$all_control_plan_results" == "120" ]]

uv run sable-ir prepare-stage1-control-audit "$control_plan_manifest" --kind clause_order \
  --tokenizer "$tokenizer" \
  --output artifacts/stage1/stage1-control-plans-20260903/audits/clause-order.template.json

print "STAGE1_RENDERER_CONTROLS_COMPLETE: reversed-order audit is ready for review"
osascript -e 'display notification "Renderer controls are complete; reversed-order audit is ready." with title "SABLE-IR Stage 1"' 2>/dev/null || true
