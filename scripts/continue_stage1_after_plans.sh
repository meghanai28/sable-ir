#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repository_root"

environment_file="$repository_root/.env.stage0.local"
plan_run="$repository_root/artifacts/stage1/stage1a-plans-20260903-recovery2"
plan_manifest="$plan_run/manifest.json"
planner_completion="$plan_run/watcher-completion.json"
tokenizer="$repository_root/artifacts/stage1/tokenizers/kimi-k2.6-7eb5002f.tiktoken.model"
log="$repository_root/artifacts/stage1/logs/stage1-continuation.log"
state="$repository_root/artifacts/stage1/stage1-continuation-state.json"

natural_id="stage1a-renders-20260903-recovery2"
natural_dir="$repository_root/artifacts/stage1/$natural_id"
surface_id="stage1-surface-20260903"
surface_dir="$repository_root/artifacts/stage1/$surface_id"
opposite_id="stage1-opposite-20260903"
opposite_dir="$repository_root/artifacts/stage1/$opposite_id"
control_plan_id="stage1-control-plans-20260903"
control_plan_dir="$repository_root/artifacts/stage1/$control_plan_id"
shuffled_id="stage1-shuffled-20260903"
shuffled_dir="$repository_root/artifacts/stage1/$shuffled_id"

write_state() {
  status=$1
  detail=$2
  temporary="$state.tmp"
  printf '{"status":"%s","detail":"%s","updated_at":"%s"}\n' \
    "$status" "$detail" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$temporary"
  mv "$temporary" "$state"
}

notify() {
  osascript -e "display notification \"$2\" with title \"$1\"" >/dev/null 2>&1 || true
}

run_logged() {
  label=$1
  shift
  write_state "running" "$label"
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$label" >> "$log"
  "$@" >> "$log" 2>&1
}

require_no_failed_attempts() {
  directory=$1
  if find "$directory/jobs" -path '*/attempts/*.json' -type f -print0 \
    | xargs -0 jq -e 'select(.succeeded == false)' >/dev/null 2>&1; then
    write_state "provider_error" "failed attempt in ${directory#$repository_root/}"
    notify "SABLE-IR Stage 1 stopped" "Provider error preserved; no retry was attempted"
    exit 1
  fi
}

require_complete_results() {
  manifest=$1
  directory=$(dirname "$manifest")
  expected=$(jq '.jobs | length' "$manifest")
  actual=$(find "$directory/jobs" -name result.json -type f | wc -l | tr -d ' ')
  if [ "$actual" -ne "$expected" ]; then
    write_state "incomplete" "${directory#$repository_root/}: $actual/$expected results"
    notify "SABLE-IR Stage 1 stopped" "A generation matrix is incomplete; no retry was attempted"
    exit 1
  fi
  require_no_failed_attempts "$directory"
}

run_render_matrix() {
  manifest=$1
  run_id=$2
  first_job=$(jq -r '.jobs[0].job_id' "$manifest")
  result="$(dirname "$manifest")/jobs/$first_job/result.json"
  if [ ! -f "$result" ]; then
    run_logged "$run_id canary generation" \
      uv run sable-ir generate-stage1-renders "$manifest" --job-id "$first_job"
  fi
  run_logged "$run_id canary Docker evaluation" \
    uv run sable-ir evaluate-stage1-renders "$manifest" \
      --repository-root "$repository_root" --job-id "$first_job"
  canary_status=$(jq -r '.status' "$result")
  if [ "$canary_status" != "generated" ]; then
    write_state "canary_failed" "$run_id canary status: $canary_status"
    notify "SABLE-IR Stage 1 stopped" "$run_id canary was not runnable"
    exit 1
  fi
  run_logged "$run_id full generation" \
    uv run sable-ir generate-stage1-renders "$manifest" --all --confirm-full-run "$run_id"
  require_complete_results "$manifest"
  run_logged "$run_id full Docker evaluation" \
    uv run sable-ir evaluate-stage1-renders "$manifest" --repository-root "$repository_root"
}

if [ ! -f "$environment_file" ]; then
  write_state "blocked" "missing ignored credential file"
  exit 2
fi
set -a
. "$environment_file"
set +a
if [ -z "${MOONSHOT_API_KEY:-}" ]; then
  write_state "blocked" "MOONSHOT_API_KEY is not set"
  exit 2
fi

write_state "waiting_for_plans" "filesystem watcher; no API calls while waiting"
while [ ! -f "$planner_completion" ]; do
  sleep 60
done
if [ "$(jq -r '.status' "$planner_completion")" != "ready_for_plan_audit" ]; then
  write_state "planner_incomplete" "see ${planner_completion#$repository_root/}"
  exit 1
fi

if [ ! -f "$natural_dir/manifest.json" ]; then
  run_logged "freeze natural renderer matrix" \
    uv run sable-ir prepare-stage1-renders "$plan_manifest" --run-id "$natural_id" \
      --repository-root "$repository_root" --run-directory "$natural_dir"
fi
run_render_matrix "$natural_dir/manifest.json" "$natural_id"

if [ ! -f "$surface_dir/manifest.json" ]; then
  run_logged "freeze repeated surface baseline" \
    uv run sable-ir prepare-stage1-surface-baseline --run-id "$surface_id" \
      --repository-root "$repository_root" --run-directory "$surface_dir"
fi
surface_manifest="$surface_dir/manifest.json"
surface_first=$(jq -r '.jobs[0].job_id' "$surface_manifest")
if [ ! -f "$surface_dir/jobs/$surface_first/result.json" ]; then
  run_logged "surface baseline canary generation" \
    uv run sable-ir generate-stage1-surface-baseline "$surface_manifest" \
      --job-id "$surface_first"
fi
run_logged "surface baseline canary Docker evaluation" \
  uv run sable-ir evaluate-stage1-surface-baseline "$surface_manifest" \
    --repository-root "$repository_root" --job-id "$surface_first"
run_logged "surface baseline full generation" \
  uv run sable-ir generate-stage1-surface-baseline "$surface_manifest" \
    --all --confirm-full-run "$surface_id"
require_complete_results "$surface_manifest"
run_logged "surface baseline full Docker evaluation" \
  uv run sable-ir evaluate-stage1-surface-baseline "$surface_manifest" \
    --repository-root "$repository_root"
run_logged "surface baseline report" \
  uv run sable-ir report-stage1-surface-baseline "$surface_manifest" \
    --output "$surface_dir/report.json"

# Control priority: opposite-policy first.
if [ ! -f "$opposite_dir/manifest.json" ]; then
  run_logged "freeze opposite-policy renderer control" \
    uv run sable-ir prepare-stage1-render-control "$plan_manifest" \
      --kind opposite_policy --run-id "$opposite_id" \
      --repository-root "$repository_root" --run-directory "$opposite_dir"
fi
run_render_matrix "$opposite_dir/manifest.json" "$opposite_id"

# Wrong-clause plans are generated next, but their renders remain blocked on the behavior-blinded
# rewrite audit. Both planner families share one immutable manifest and retain one-attempt behavior.
if [ ! -f "$control_plan_dir/manifest.json" ]; then
  run_logged "freeze wrong-clause and clause-order planner controls" \
    uv run sable-ir prepare-stage1-control-plans "$plan_manifest" \
      --run-id "$control_plan_id" --repository-root "$repository_root" \
      --run-directory "$control_plan_dir" --tokenizer "$tokenizer"
fi
control_manifest="$control_plan_dir/manifest.json"
wrong_first=$(jq -r '.jobs[] | select(.kind == "wrong_clause") | .job_id' "$control_manifest" \
  | head -n 1)
if [ ! -f "$control_plan_dir/jobs/$wrong_first/result.json" ]; then
  run_logged "wrong-clause planner canary" \
    uv run sable-ir generate-stage1-control-plans "$control_manifest" --kind wrong_clause \
      --job-id "$wrong_first"
fi
run_logged "wrong-clause planner matrix" \
  uv run sable-ir generate-stage1-control-plans "$control_manifest" --kind wrong_clause \
    --all --confirm-full-run "$control_plan_id"
require_no_failed_attempts "$control_plan_dir"
run_logged "prepare wrong-clause behavior-blinded audit" \
  uv run sable-ir prepare-stage1-control-audit "$control_manifest" --kind wrong_clause \
    --tokenizer "$tokenizer" --repository-root "$repository_root" \
    --output "$control_plan_dir/wrong-clause-audit.json"

# Shuffled-task is descriptive and can finish while the wrong-clause audit awaits review.
if [ ! -f "$shuffled_dir/manifest.json" ]; then
  run_logged "freeze shuffled-task renderer control" \
    uv run sable-ir prepare-stage1-render-control "$plan_manifest" \
      --kind shuffled_task --run-id "$shuffled_id" \
      --repository-root "$repository_root" --run-directory "$shuffled_dir"
fi
run_render_matrix "$shuffled_dir/manifest.json" "$shuffled_id"

# Reversed document order is deliberately last.
order_first=$(jq -r '.jobs[] | select(.kind == "clause_order") | .job_id' "$control_manifest" \
  | head -n 1)
if [ ! -f "$control_plan_dir/jobs/$order_first/result.json" ]; then
  run_logged "clause-order planner canary" \
    uv run sable-ir generate-stage1-control-plans "$control_manifest" --kind clause_order \
      --job-id "$order_first"
fi
run_logged "clause-order planner matrix" \
  uv run sable-ir generate-stage1-control-plans "$control_manifest" --kind clause_order \
    --all --confirm-full-run "$control_plan_id"
require_no_failed_attempts "$control_plan_dir"
run_logged "prepare clause-order behavior-blinded audit" \
  uv run sable-ir prepare-stage1-control-audit "$control_manifest" --kind clause_order \
    --tokenizer "$tokenizer" --repository-root "$repository_root" \
    --output "$control_plan_dir/clause-order-audit.json"

write_state "manual_audits_required" \
  "natural plan, wrong-clause rewrite, and clause-order selection audits are ready"
notify "SABLE-IR Stage 1" "Automatic runs finished; three behavior-blinded audits are ready"
