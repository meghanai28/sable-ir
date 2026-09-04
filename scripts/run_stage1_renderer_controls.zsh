#!/bin/zsh
set -euo pipefail

# Frozen lean Stage 1D execution. This script deliberately has no clause-order or shuffled-task
# branch and never prepares a recovery/retry manifest automatically.
readonly repository_root="${0:A:h:h}"
readonly plan_manifest="artifacts/stage1/stage1a-plans-20260903-recovery3/manifest.json"
readonly plan_audit="artifacts/stage1/stage1a-plans-20260903-recovery3/audits/stage1c-plan-audit.completed.json"
readonly natural_manifest="artifacts/stage1/stage1a-renders-20260903-recovery4/manifest.json"
readonly surface_report="artifacts/stage1/stage1-surface-20260903/report.json"
readonly control_plan_manifest="artifacts/stage1/stage1-control-plans-20260904-lengthfix9/manifest.json"
readonly selection="artifacts/stage1/stage1-lean-control-selection-20260904-v2.json"
readonly wrong_audit="artifacts/stage1/stage1-control-plans-20260904-lengthfix9/audits/wrong-clause-lean-v2.completed.json"
readonly opposite_id="stage1-opposite-lean-20260904-v2"
readonly opposite_manifest="artifacts/stage1/${opposite_id}/manifest.json"
readonly wrong_id="stage1-wrong-clause-lean-20260904-v2"
readonly wrong_manifest="artifacts/stage1/${wrong_id}/manifest.json"
readonly stage0_report="artifacts/stage0/stage0-smoke-20260902-timeout-recovery/reports/final/stage0-report.json"
readonly report_dir="artifacts/stage1/reports"

cd "$repository_root"
set -a
source .env.stage0.local
set +a

mkdir -p "$report_dir"

if [[ ! -f "$wrong_audit" ]]; then
  print -u2 "missing completed behavior-blinded wrong-clause audit: $wrong_audit"
  exit 1
fi

uv run sable-ir validate-stage1-control-audit "$wrong_audit" "$control_plan_manifest"

if [[ ! -f "$opposite_manifest" ]]; then
  uv run sable-ir prepare-stage1-render-control "$plan_manifest" \
    --kind opposite_policy --lean-selection "$selection" --run-id "$opposite_id" \
    --run-directory "artifacts/stage1/$opposite_id"
fi

if [[ ! -f "$wrong_manifest" ]]; then
  uv run sable-ir prepare-stage1-render-control "$plan_manifest" --kind wrong_clause \
    --control-plan-manifest "$control_plan_manifest" --control-plan-audit "$wrong_audit" \
    --lean-selection "$selection" --run-id "$wrong_id" \
    --run-directory "artifacts/stage1/$wrong_id"
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
    | xargs -0 jq -s -e '
      all(.[]; .reasoning_content_present == false)
    ' >/dev/null 2>&1; then
    print -u2 "stopped: nonthinking renderer returned a reasoning trace"
    exit 1
  fi
}

function run_renderer_control() {
  local kind="$1"
  local run_id="$2"
  local manifest="$3"
  local behavior_output="$4"
  local canary
  canary="$(jq -r '.jobs[0].job_id' "$manifest")"
  print "starting lean ${kind} renderer control"

  if [[ ! -f "${manifest:h}/jobs/$canary/result.json" ]]; then
    uv run sable-ir generate-stage1-renders "$manifest" --job-id "$canary"
  fi
  jq -e '
    .status == "generated"
    and .finish_reason != "length"
    and .reasoning_content_present == false
  ' "${manifest:h}/jobs/$canary/result.json" >/dev/null
  if [[ ! -f "${manifest:h}/jobs/$canary/evaluation.json" ]]; then
    uv run sable-ir evaluate-stage1-renders "$manifest" --job-id "$canary"
  fi
  uv run sable-ir generate-stage1-renders "$manifest" --all --confirm-full-run "$run_id"
  require_complete_without_provider_error "$manifest"
  uv run sable-ir evaluate-stage1-renders "$manifest"
  if [[ ! -f "$behavior_output" ]]; then
    uv run sable-ir report-stage1-behavior "$manifest" "$plan_manifest" "$plan_audit" \
      "$surface_report" "$stage0_report" --output "$behavior_output"
  fi
}

if [[ ! -f "$report_dir/stage1-natural-behavior-20260904.json" ]]; then
  uv run sable-ir report-stage1-behavior "$natural_manifest" "$plan_manifest" \
    "$plan_audit" "$surface_report" "$stage0_report" \
    --output "$report_dir/stage1-natural-behavior-20260904.json"
fi

run_renderer_control opposite_policy "$opposite_id" "$opposite_manifest" \
  "$report_dir/stage1-opposite-lean-behavior-20260904.json"
run_renderer_control wrong_clause "$wrong_id" "$wrong_manifest" \
  "$report_dir/stage1-wrong-clause-lean-behavior-20260904.json"

set +e
uv run sable-ir report-stage1 \
  --stage0-report "$stage0_report" \
  --natural-behavior "$report_dir/stage1-natural-behavior-20260904.json" \
  --opposite-behavior "$report_dir/stage1-opposite-lean-behavior-20260904.json" \
  --wrong-clause-behavior "$report_dir/stage1-wrong-clause-lean-behavior-20260904.json" \
  --length-report artifacts/stage1/stage1a-plans-20260903-recovery3/analysis/stage1b-lengths.json \
  --plan-audit "$plan_audit" --wrong-clause-control-audit "$wrong_audit" \
  --control-plan-manifest "$control_plan_manifest" --lean-selection "$selection" \
  --output "$report_dir/stage1-report-lean-for-review-v2-20260904.json"
report_status=$?
set -e
if [[ $report_status -ne 1 ]]; then
  print -u2 "unexpected Stage 1 report exit status: $report_status"
  exit 1
fi

print "STAGE1_LEAN_CONTROLS_COMPLETE: report ready for manual review"
osascript -e 'display notification "Lean Stage 1 controls and report are ready." with title "SABLE-IR Stage 1"' >/dev/null 2>&1 || :
