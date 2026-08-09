#!/usr/bin/env bash
# Launches the dashboard the way that's confirmed to work regardless of whether the
# bare `streamlit` command is on PATH (it often isn't -- see app.py's own docstring
# and README.md). Run from anywhere:
#   bash master_dashboard/run.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE/.."
python3 -m streamlit run master_dashboard/app.py "$@"
