#!/bin/sh
set -eu

# Compatibility entry point for the superseded full-control workflow. The lean runner refuses to
# start until the sampled wrong-clause audit is complete and contains no shuffled/order branch.
repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec /bin/zsh "$repository_root/scripts/run_stage1_renderer_controls.zsh"
