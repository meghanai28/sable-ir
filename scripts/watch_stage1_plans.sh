#!/bin/sh
set -eu

if [ "$#" -ne 3 ]; then
  echo "usage: watch_stage1_plans.sh PID PLAN_MANIFEST REPOSITORY_ROOT" >&2
  exit 2
fi

planner_pid=$1
plan_manifest=$2
repository_root=$3
run_directory=$(dirname "$plan_manifest")
tokenizer="$repository_root/artifacts/stage1/tokenizers/kimi-k2.6-7eb5002f.tiktoken.model"
length_report="$run_directory/analysis/stage1b-lengths.json"
audit_packet="$run_directory/audits/stage1c-plan-audit-template.json"
completion="$run_directory/watcher-completion.json"

while kill -0 "$planner_pid" 2>/dev/null; do
  sleep 60
done

result_count=$(find "$run_directory/jobs" -name result.json -type f | wc -l | tr -d ' ')
generated_count=$(find "$run_directory/jobs" -name result.json -type f -print0 \
  | xargs -0 jq -r '.status' | awk '$0 == "generated" {count++} END {print count+0}')

if [ "$result_count" -ne 180 ] || [ "$generated_count" -ne 180 ]; then
  printf '{"status":"planner_incomplete","results":%s,"generated":%s}\n' \
    "$result_count" "$generated_count" > "$completion"
  osascript -e 'display notification "Planner stopped before 180 valid plans" with title "SABLE-IR Stage 1"' \
    >/dev/null 2>&1 || true
  exit 1
fi

cd "$repository_root"
uv run sable-ir fetch-stage1-tokenizer "$tokenizer"
uv run sable-ir analyze-stage1-lengths "$plan_manifest" \
  --tokenizer "$tokenizer" --output "$length_report"
uv run sable-ir prepare-stage1-plan-audit "$plan_manifest" \
  --repository-root "$repository_root" --output "$audit_packet"

printf '{"status":"ready_for_plan_audit","results":180,"generated":180,"length_report":"%s","audit_packet":"%s"}\n' \
  "$length_report" "$audit_packet" > "$completion"
osascript -e 'display notification "180 plans complete; length report and audit packet are ready" with title "SABLE-IR Stage 1"' \
  >/dev/null 2>&1 || true
