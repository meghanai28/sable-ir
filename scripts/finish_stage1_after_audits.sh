#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"
set -a
. "$repository_root/.env.stage0.local"
set +a

plan_run="$repository_root/artifacts/stage1/stage1a-plans-20260903-recovery2"
plan_manifest="$plan_run/manifest.json"
plan_audit="$plan_run/audits/stage1c-plan-audit-template.json"
length_report="$plan_run/analysis/stage1b-lengths.json"
natural_dir="$repository_root/artifacts/stage1/stage1a-renders-20260903-recovery2"
surface_dir="$repository_root/artifacts/stage1/stage1-surface-20260903"
opposite_dir="$repository_root/artifacts/stage1/stage1-opposite-20260903"
shuffled_dir="$repository_root/artifacts/stage1/stage1-shuffled-20260903"
control_plan_dir="$repository_root/artifacts/stage1/stage1-control-plans-20260903"
wrong_audit="$control_plan_dir/wrong-clause-audit.json"
order_audit="$control_plan_dir/clause-order-audit.json"
wrong_id="stage1-wrong-clause-20260903"
wrong_dir="$repository_root/artifacts/stage1/$wrong_id"
stage0_report="$repository_root/artifacts/stage0/stage0-smoke-20260902-timeout-recovery/reports/final/stage0-report.json"
report_dir="$repository_root/artifacts/stage1/reports"
log="$repository_root/artifacts/stage1/logs/stage1-finish-after-audits.log"

run_logged() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$log"
  shift
  "$@" >> "$log" 2>&1
}

require_complete_without_provider_error() {
  manifest=$1
  directory=$(dirname "$manifest")
  expected=$(jq '.jobs | length' "$manifest")
  actual=$(find "$directory/jobs" -name result.json -type f | wc -l | tr -d ' ')
  if [ "$actual" -ne "$expected" ]; then
    echo "stopped: $actual/$expected results; inspect the preserved attempt and do not retry" \
      >> "$log"
    exit 1
  fi
  if find "$directory/jobs" -path '*/attempts/*.json' -type f -print0 \
    | xargs -0 jq -e 'select(.succeeded == false)' >/dev/null 2>&1; then
    echo "stopped: provider error preserved; no retry attempted" >> "$log"
    exit 1
  fi
}

uv run sable-ir summarize-stage1-plan-audit "$plan_audit" "$plan_manifest" >> "$log"
uv run sable-ir validate-stage1-control-audit "$wrong_audit" \
  "$control_plan_dir/manifest.json" >> "$log"
uv run sable-ir validate-stage1-control-audit "$order_audit" \
  "$control_plan_dir/manifest.json" >> "$log"

if [ ! -f "$wrong_dir/manifest.json" ]; then
  run_logged "freeze wrong-clause renderer control" \
    uv run sable-ir prepare-stage1-render-control "$plan_manifest" --kind wrong_clause \
      --control-plan-manifest "$control_plan_dir/manifest.json" \
      --control-plan-audit "$wrong_audit" --run-id "$wrong_id" \
      --repository-root "$repository_root" --run-directory "$wrong_dir"
fi
wrong_manifest="$wrong_dir/manifest.json"
wrong_first=$(jq -r '.jobs[0].job_id' "$wrong_manifest")
if [ ! -f "$wrong_dir/jobs/$wrong_first/result.json" ]; then
  run_logged "wrong-clause renderer canary" \
    uv run sable-ir generate-stage1-renders "$wrong_manifest" --job-id "$wrong_first"
fi
if [ "$(jq -r '.status' "$wrong_dir/jobs/$wrong_first/result.json")" != "generated" ]; then
  echo "stopped: wrong-clause renderer canary was not runnable" >> "$log"
  exit 1
fi
run_logged "wrong-clause canary Docker evaluation" \
  uv run sable-ir evaluate-stage1-renders "$wrong_manifest" \
    --repository-root "$repository_root" --job-id "$wrong_first"
run_logged "wrong-clause renderer matrix" \
  uv run sable-ir generate-stage1-renders "$wrong_manifest" --all \
    --confirm-full-run "$wrong_id"
require_complete_without_provider_error "$wrong_manifest"
run_logged "wrong-clause Docker evaluation" \
  uv run sable-ir evaluate-stage1-renders "$wrong_manifest" \
    --repository-root "$repository_root"

mkdir -p "$report_dir"
for item in \
  "natural:$natural_dir" \
  "opposite:$opposite_dir" \
  "shuffled:$shuffled_dir" \
  "wrong_clause:$wrong_dir"
do
  name=${item%%:*}
  directory=${item#*:}
  run_logged "aggregate $name behavior" \
    uv run sable-ir report-stage1-behavior "$directory/manifest.json" "$plan_manifest" \
      "$plan_audit" "$surface_dir/report.json" "$stage0_report" \
      --output "$report_dir/$name-behavior.json"
done

# This first report intentionally remains manual_review_required. After auditing it, produce the
# canonical report with the same command plus --final-manual-review-passed and a new output path.
uv run sable-ir report-stage1 \
  --stage0-report "$stage0_report" \
  --natural-behavior "$report_dir/natural-behavior.json" \
  --opposite-behavior "$report_dir/opposite-behavior.json" \
  --shuffled-behavior "$report_dir/shuffled-behavior.json" \
  --wrong-clause-behavior "$report_dir/wrong_clause-behavior.json" \
  --length-report "$length_report" --plan-audit "$plan_audit" \
  --wrong-clause-control-audit "$wrong_audit" \
  --clause-order-control-audit "$order_audit" \
  --control-plan-manifest "$control_plan_dir/manifest.json" \
  --output "$report_dir/stage1-report-for-final-review.json" >> "$log" 2>&1 || true

osascript -e 'display notification "Stage 1 report is ready for final review" with title "SABLE-IR"' \
  >/dev/null 2>&1 || true
