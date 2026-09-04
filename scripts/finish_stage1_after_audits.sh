#!/bin/sh
set -eu

# Compatibility entry point. The active Stage 1 design is the lean amendment; the former full
# control runner is intentionally unreachable so this script cannot spend on shuffled-task or
# clause-order jobs.
repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec /bin/zsh "$repository_root/scripts/run_stage1_renderer_controls.zsh"
