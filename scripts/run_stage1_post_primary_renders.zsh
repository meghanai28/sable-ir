#!/bin/zsh
set -euo pipefail

readonly repository_root="${0:A:h:h}"
readonly selection="artifacts/stage1/stage1-post-primary-robustness-selection-20260904.json"
readonly expected_selection_sha="fe53b4dfb97f9ad4727c705ec66aa8b47b185b162a7bb0c122a4ee36ee6f243f"
readonly plan_manifest="artifacts/stage1/stage1a-plans-20260903-recovery3/manifest.json"
readonly plan_audit="artifacts/stage1/stage1a-plans-20260903-recovery3/audits/stage1c-plan-audit.completed.json"
readonly control_manifest="artifacts/stage1/stage1-control-plans-20260904-clause-reparse1/manifest.json"
readonly clause_audit="${control_manifest:h}/audits/clause-order-post-primary.completed.json"
readonly clause_id="stage1-clause-order-post-primary-20260904"
readonly clause_manifest="artifacts/stage1/$clause_id/manifest.json"
readonly shuffled_id="stage1-shuffled-task-post-primary-20260904"
readonly shuffled_manifest="artifacts/stage1/$shuffled_id/manifest.json"
readonly surface_report="artifacts/stage1/stage1-surface-20260903/report.json"
readonly stage0_report="artifacts/stage0/stage0-smoke-20260902-timeout-recovery/reports/final/stage0-report.json"
readonly natural_behavior="artifacts/stage1/reports/stage1-natural-behavior-20260904.json"
readonly clause_behavior="artifacts/stage1/reports/stage1-clause-order-post-primary-behavior-20260904.json"
readonly shuffled_behavior="artifacts/stage1/reports/stage1-shuffled-task-post-primary-behavior-20260904.json"
readonly addendum_report="artifacts/stage1/reports/stage1-robustness-addendum-20260904.json"

cd "$repository_root"
set -a
source .env.stage0.local
set +a

actual_selection_sha="$(shasum -a 256 "$selection" | awk '{print $1}')"
if [[ "$actual_selection_sha" != "$expected_selection_sha" ]]; then
  print -u2 "post-primary selection hash changed; refusing provider calls"
  exit 1
fi
if [[ ! -f "$clause_audit" ]]; then
  print -u2 "completed behavior-blinded clause-order audit is missing"
  exit 1
fi
uv run sable-ir validate-stage1-control-audit "$clause_audit" "$control_manifest"

if [[ ! -f "$clause_manifest" ]]; then
  uv run sable-ir prepare-stage1-render-control "$plan_manifest" \
    --kind clause_order \
    --control-plan-manifest "$control_manifest" \
    --control-plan-audit "$clause_audit" \
    --post-primary-selection "$selection" \
    --run-id "$clause_id" \
    --run-directory "${clause_manifest:h}"
fi
if [[ ! -f "$shuffled_manifest" ]]; then
  uv run sable-ir prepare-stage1-render-control "$plan_manifest" \
    --kind shuffled_task \
    --post-primary-selection "$selection" \
    --run-id "$shuffled_id" \
    --run-directory "${shuffled_manifest:h}"
fi

function require_complete_without_provider_error() {
  local manifest="$1"
  local directory="${manifest:h}"
  local expected
  local actual
  expected="$(jq '.jobs | length' "$manifest")"
  actual="$(find "$directory/jobs" -name result.json -type f | wc -l | tr -d ' ')"
  if [[ "$actual" != "$expected" ]]; then
    print -u2 "stopped: $actual/$expected results; inspect the preserved attempt; no retry made"
    exit 1
  fi
  if ! find "$directory/jobs" -path '*/attempts/*.json' -type f -print0 \
    | xargs -0 jq -s -e 'all(.[]; .succeeded == true)' >/dev/null 2>&1; then
    print -u2 "stopped: provider error preserved; no retry made"
    exit 1
  fi
  if ! find "$directory/jobs" -name result.json -type f -print0 \
    | xargs -0 jq -s -e 'all(.[]; .reasoning_content_present == false)' \
      >/dev/null 2>&1; then
    print -u2 "stopped: nonthinking renderer returned a reasoning trace"
    exit 1
  fi
}

function require_complete_result() {
  local manifest="$1"
  local job_id="$2"
  local directory="${manifest:h}"
  local attempt="$directory/jobs/$job_id/attempts/attempt-01.json"
  local result="$directory/jobs/$job_id/result.json"
  if [[ ! -f "$attempt" ]] || ! jq -e '.succeeded == true' "$attempt" >/dev/null; then
    print -u2 "provider attempt failed or is missing for $job_id; no retry made"
    exit 1
  fi
  if [[ ! -f "$result" ]] || ! jq -e '.reasoning_content_present == false' \
    "$result" >/dev/null; then
    print -u2 "renderer result is missing or contains reasoning for $job_id"
    exit 1
  fi
}

function run_condition() {
  local run_id="$1"
  local manifest="$2"
  local behavior="$3"
  typeset -a jobs
  jobs=("${(@f)$(jq -r '.jobs[].job_id' "$manifest")}")
  local canary="${jobs[1]}"
  if [[ ! -f "${manifest:h}/jobs/$canary/result.json" ]]; then
    uv run sable-ir generate-stage1-renders "$manifest" --job-id "$canary"
  fi
  require_complete_result "$manifest" "$canary"
  if [[ ! -f "${manifest:h}/jobs/$canary/evaluation.json" ]]; then
    uv run sable-ir evaluate-stage1-renders "$manifest" --job-id "$canary"
  fi
  for job_id in "${jobs[@]}"; do
    if [[ ! -f "${manifest:h}/jobs/$job_id/result.json" ]]; then
      uv run sable-ir generate-stage1-renders "$manifest" --job-id "$job_id"
    fi
    require_complete_result "$manifest" "$job_id"
  done
  require_complete_without_provider_error "$manifest"
  uv run sable-ir evaluate-stage1-renders "$manifest"
  if [[ ! -f "$behavior" ]]; then
    uv run sable-ir report-stage1-behavior "$manifest" "$plan_manifest" "$plan_audit" \
      "$surface_report" "$stage0_report" --output "$behavior"
  fi
}

run_condition "$clause_id" "$clause_manifest" "$clause_behavior"
run_condition "$shuffled_id" "$shuffled_manifest" "$shuffled_behavior"

if [[ ! -f "$addendum_report" ]]; then
  uv run sable-ir report-stage1-robustness-addendum \
    --selection "$selection" \
    --canonical-stage1-report artifacts/stage1/reports/stage1-report.json \
    --natural-behavior "$natural_behavior" \
    --control-plan-manifest "$control_manifest" \
    --clause-order-audit "$clause_audit" \
    --clause-order-render-manifest "$clause_manifest" \
    --clause-order-behavior "$clause_behavior" \
    --shuffled-render-manifest "$shuffled_manifest" \
    --shuffled-behavior "$shuffled_behavior" \
    --output "$addendum_report"
fi

print "STAGE1_POST_PRIMARY_ROBUSTNESS_COMPLETE: 48/48 descriptive code outputs evaluated"
osascript -e 'display notification "Stage 1 post-primary robustness addendum is complete." with title "SABLE-IR Stage 1 addendum"' >/dev/null 2>&1 || :
