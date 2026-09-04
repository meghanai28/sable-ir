#!/bin/zsh
set -euo pipefail

readonly repository_root="${0:A:h:h}"
readonly selection="artifacts/stage1/stage1-post-primary-robustness-selection-20260904.json"
readonly control_manifest="artifacts/stage1/stage1-control-plans-20260904-clause-reparse1/manifest.json"
readonly expected_selection_sha="fe53b4dfb97f9ad4727c705ec66aa8b47b185b162a7bb0c122a4ee36ee6f243f"

cd "$repository_root"
set -a
source .env.stage0.local
set +a

actual_selection_sha="$(shasum -a 256 "$selection" | awk '{print $1}')"
if [[ "$actual_selection_sha" != "$expected_selection_sha" ]]; then
  print -u2 "post-primary selection hash changed; refusing provider calls"
  exit 1
fi

typeset -a jobs
jobs=("${(@f)$(jq -r '.base_cell_ids[] + "__control_clause_order"' "$selection")}")
if [[ ${#jobs[@]} -ne 24 ]]; then
  print -u2 "post-primary planner selection is not 24 jobs"
  exit 1
fi

function require_valid_plan() {
  local job_id="$1"
  local result="${control_manifest:h}/jobs/$job_id/result.json"
  local attempt="${control_manifest:h}/jobs/$job_id/attempts/attempt-01.json"
  if [[ ! -f "$attempt" ]] || ! jq -e '.succeeded == true' "$attempt" >/dev/null; then
    print -u2 "provider attempt failed or is missing for $job_id; no retry made"
    exit 1
  fi
  if [[ ! -f "$result" ]] || ! jq -e '
    .status == "generated"
    and .finish_reason != "length"
    and .plan_path != null
    and .thinking_requested == "enabled"
  ' "$result" >/dev/null; then
    print -u2 "planner canary/output is not a complete plan for $job_id; no retry made"
    exit 1
  fi
}

readonly canary="${jobs[1]}"
if [[ ! -f "${control_manifest:h}/jobs/$canary/result.json" ]]; then
  uv run sable-ir generate-stage1-control-plans "$control_manifest" \
    --kind clause_order --job-id "$canary"
fi
require_valid_plan "$canary"

for job_id in "${jobs[@]}"; do
  if [[ ! -f "${control_manifest:h}/jobs/$job_id/result.json" ]]; then
    uv run sable-ir generate-stage1-control-plans "$control_manifest" \
      --kind clause_order --job-id "$job_id"
  fi
  require_valid_plan "$job_id"
done

uv run sable-ir prepare-stage1-control-audit "$control_manifest" \
  --kind clause_order \
  --tokenizer artifacts/stage1/tokenizer/kimi-k2.6.tiktoken \
  --post-primary-selection "$selection" \
  --output "${control_manifest:h}/audits/clause-order-post-primary.template.json"

print "STAGE1_POST_PRIMARY_PLANNERS_COMPLETE: 24/24; behavior-blinded audit template ready"
osascript -e 'display notification "24 clause-order plans are ready for behavior-blinded audit." with title "SABLE-IR Stage 1 addendum"' >/dev/null 2>&1 || :
