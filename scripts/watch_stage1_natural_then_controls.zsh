#!/bin/zsh
set -euo pipefail

# Compatibility entry point for the retired full-control watcher. The event-driven lean runner
# preserves the canary barrier and stops on provider errors without automatic retries.
readonly repository_root="${0:A:h:h}"
exec /bin/zsh "$repository_root/scripts/run_stage1_renderer_controls.zsh"
