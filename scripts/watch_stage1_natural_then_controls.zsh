#!/bin/zsh
set -euo pipefail

if (( $# != 1 )) || [[ "$1" != <-> ]]; then
  print -u2 "usage: $0 NATURAL_GENERATION_PID"
  exit 2
fi

readonly natural_generation_pid="$1"
readonly repository_root="${0:A:h:h}"
readonly natural_plan_manifest="artifacts/stage1/stage1a-plans-20260903-recovery3/manifest.json"
readonly natural_render_manifest="artifacts/stage1/stage1a-renders-20260903-recovery3/manifest.json"
readonly surface_manifest="artifacts/stage1/stage1-surface-20260903/manifest.json"
readonly control_manifest="artifacts/stage1/stage1-control-plans-20260903/manifest.json"
readonly surface_report="artifacts/stage1/stage1-surface-20260903/report.json"
readonly surface_canary="path_symlink_report__stage1_surface__r00"
readonly wrong_clause_canary="command_executable__plan_a__freeform__concise__p00__control_wrong_clause"

cd "$repository_root"

while ps -p "$natural_generation_pid" -o command= 2>/dev/null \
  | rg -q "generate-stage1-renders .*stage1a-renders-20260903-recovery3"; do
  sleep 60
done

natural_status="$(uv run sable-ir status-stage1a \
  "$natural_plan_manifest" --render-manifest "$natural_render_manifest")"
print -r -- "$natural_status"
print -r -- "$natural_status" | jq -e \
  '.pending_plans == 0 and .pending_renders == 0 and .generated_plans == 180' >/dev/null

uv run sable-ir evaluate-stage1-renders "$natural_render_manifest"

set -a
source .env.stage0.local
set +a

uv run sable-ir generate-stage1-surface-baseline "$surface_manifest" \
  --job-id "$surface_canary"
uv run sable-ir evaluate-stage1-surface-baseline "$surface_manifest" \
  --job-id "$surface_canary"
uv run sable-ir generate-stage1-surface-baseline "$surface_manifest" --all \
  --confirm-full-run stage1-surface-20260903

readonly surface_results="$(find artifacts/stage1/stage1-surface-20260903/jobs \
  -name result.json -type f | wc -l | tr -d ' ')"
[[ "$surface_results" == "20" ]]
uv run sable-ir evaluate-stage1-surface-baseline "$surface_manifest"
uv run sable-ir report-stage1-surface-baseline "$surface_manifest" --output "$surface_report"

uv run sable-ir generate-stage1-control-plans "$control_manifest" \
  --kind wrong_clause --job-id "$wrong_clause_canary"
uv run sable-ir generate-stage1-control-plans "$control_manifest" \
  --kind wrong_clause --all --confirm-full-run stage1-control-plans-20260903

readonly wrong_clause_results="$(find artifacts/stage1/stage1-control-plans-20260903/jobs \
  -name result.json -type f | wc -l | tr -d ' ')"
[[ "$wrong_clause_results" == "60" ]]

print "STAGE1_WATCHER_PHASE_COMPLETE: natural and surface evaluated; wrong-clause plans ready for audit"
osascript -e 'display notification "Natural/surface evaluation and wrong-clause plans are ready." with title "SABLE-IR Stage 1"' 2>/dev/null || true
