#!/usr/bin/env bash
set -euo pipefail
ROOT="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
case "${1:-help}" in
  help|-h|--help)
    echo 'SO101: ./so101.sh workbench [doctor|start|help] | doctor | check | follower'
    echo 'workbench opens the existing simulation workbench; doctor checks its environment without starting a task.'
    echo 'check only checks the offline file layout. follower is the separate hardware web application.'
    ;;
  workbench)
    shift
    exec bash "$ROOT/tools/workbench.sh" "$@"
    ;;
  doctor)
    shift
    exec bash "$ROOT/tools/workbench.sh" doctor "$@"
    ;;
  check) exec /usr/bin/python3 "$ROOT/tools/check_layout.py" ;;
  follower)
    shift
    exec /usr/bin/python3 "$ROOT/mint_follower_demo/app.py" "$@"
    ;;
  *) echo "Unknown command: $1" >&2; exit 2 ;;
esac
