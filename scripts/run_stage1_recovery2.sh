#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
environment_file="$repository_root/.env.stage0.local"
manifest="$repository_root/artifacts/stage1/stage1a-plans-20260903-recovery2/manifest.json"

if [ ! -f "$environment_file" ]; then
  echo "missing ignored credential file: $environment_file" >&2
  exit 2
fi

set -a
. "$environment_file"
set +a

if [ -z "${MOONSHOT_API_KEY:-}" ]; then
  echo "MOONSHOT_API_KEY is not set" >&2
  exit 2
fi

cd "$repository_root"
exec uv run sable-ir generate-stage1-plans "$manifest" \
  --all \
  --confirm-full-run stage1a-plans-20260903-recovery2
