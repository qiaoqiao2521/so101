#!/usr/bin/env bash
# Isolated local CPU simulation runtime; never imports the hardware Runtime.
set -euo pipefail
MODULE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TASK_VENV="${SO101_SAFETY_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/so101-safety/venv}"
command -v uv >/dev/null || { echo 'Install uv before deploying this local simulation.' >&2; exit 2; }
if [[ ! -x "$TASK_VENV/bin/python" ]]; then
    uv venv --python 3.12 "$TASK_VENV"
fi
uv pip install --python "$TASK_VENV/bin/python" -r "$MODULE_DIR/requirements.txt"
uv pip check --python "$TASK_VENV/bin/python"
case "${1:-}" in
    --check)
        shift
        "$TASK_VENV/bin/python" -m unittest discover -s "$MODULE_DIR" -p 'test_*.py'
        exec "$TASK_VENV/bin/python" "$MODULE_DIR/run_tracking_check.py" "$@"
        ;;
    --tracking-check)
        shift
        exec "$TASK_VENV/bin/python" "$MODULE_DIR/run_tracking_check.py" "$@"
        ;;
    *) exec "$TASK_VENV/bin/python" "$MODULE_DIR/run_demo.py" "$@" ;;
esac
