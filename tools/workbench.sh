#!/usr/bin/env bash
# Delegate to the existing FishBot workbench; no simulator or device starts here.
set -euo pipefail

SO101_PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
command="${1:-start}"
if (( $# )); then shift; fi

usage() {
  cat <<'EOF'
SO101 simulation workbench
  ./so101.sh workbench doctor [options]   Check the existing workbench environment
  ./so101.sh workbench start [options]    Start the existing workbench web service
  ./so101.sh doctor [options]            Shortcut for workbench doctor

Set WORKBENCH_ROOT or FISHBOT_ROOT to the FishBot repository root (or its
apps/fishbot-control-station directory). Without configuration, look beside this
SO101 checkout for fishbot-ros2-slam-tools or fishbot. SO101_ROOT is this checkout;
an explicitly configured SO101_PYTHON is passed through unchanged.

Use /so101-station in the workbench for the existing MuJoCo workcell. Starting its
web service does not submit a simulation task or connect the follower hardware.
Remaining options are passed unchanged to ./fishbot.sh workbench doctor|start.
EOF
}

case "$command" in
  help|-h|--help) usage; exit 0 ;;
  doctor|start) ;;
  *) printf 'Unknown workbench command: %s\n' "$command" >&2; usage >&2; exit 2 ;;
esac

repository_root() {
  local candidate="$1" resolved
  [[ -d "$candidate" ]] || return 1
  resolved="$(cd -- "$candidate" && pwd -P)"
  if [[ -f "$resolved/fishbot.sh" ]]; then
    printf '%s\n' "$resolved"
  elif [[ "$resolved" == */apps/fishbot-control-station && -f "$resolved/../../fishbot.sh" ]]; then
    (cd -- "$resolved/../.." && pwd -P)
  else
    return 1
  fi
}

workbench_repo=''
if [[ -n "${WORKBENCH_ROOT:-}" || -n "${FISHBOT_ROOT:-}" ]]; then
  configured_root="${WORKBENCH_ROOT:-${FISHBOT_ROOT:-}}"
  if ! workbench_repo="$(repository_root "$configured_root")"; then
    printf 'Cannot find fishbot.sh at configured workbench: %s\n' "$configured_root" >&2
    printf 'Set WORKBENCH_ROOT or FISHBOT_ROOT to the FishBot repository root or apps/fishbot-control-station.\n' >&2
    exit 2
  fi
else
  for candidate in "$SO101_PROJECT_ROOT/../fishbot-ros2-slam-tools" "$SO101_PROJECT_ROOT/../fishbot"; do
    if workbench_repo="$(repository_root "$candidate")"; then break; fi
  done
  if [[ -z "$workbench_repo" ]]; then
    printf 'FishBot workbench was not found beside this SO101 checkout.\n' >&2
    printf 'Set WORKBENCH_ROOT=/path/to/fishbot-ros2-slam-tools, then run ./so101.sh workbench doctor.\n' >&2
    exit 2
  fi
fi

export SO101_ROOT="$SO101_PROJECT_ROOT"
exec bash "$workbench_repo/fishbot.sh" workbench "$command" "$@"
