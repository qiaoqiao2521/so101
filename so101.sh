#!/usr/bin/env bash
set -euo pipefail
ROOT="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
case "${1:-help}" in
  help|-h|--help)
    echo 'SO101: ./so101.sh check | follower | safety [--render | --check | --tracking-check]'
    echo 'check is offline. follower starts the web application; no automatic serial connection is requested.'
    ;;
  check) exec /usr/bin/python3 "$ROOT/tools/check_layout.py" ;;
  safety)
    shift
    exec bash "$ROOT/experiments/multilink-safety/deploy_local.sh" "$@"
    ;;
  follower)
    shift
    exec /usr/bin/python3 "$ROOT/mint_follower_demo/app.py" "$@"
    ;;
  *) echo "Unknown command: $1" >&2; exit 2 ;;
esac
