#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd -- "$here/../.." && pwd)"
demo_cache="${SO101_GRASPGENX_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/so101-graspgenx}"
python="$demo_cache/upstream/.venv/bin/python"
[[ $# -ge 1 ]] || { echo 'Usage: reviewed.sh <wizard-output-directory> [seed] [count]' >&2; exit 1; }
[[ "$(git -C "$demo_cache/upstream" rev-parse HEAD)" == b9429097728cb1c430dd78b92edf17ba318aad03 ]] || exit 1
[[ -z "$(git -C "$demo_cache/upstream" status --porcelain --untracked-files=no)" ]] || exit 1
out="$here/output/reviewed-$(date +%Y%m%d-%H%M%S)-$$"
export MUJOCO_GL=egl
"$python" "$here/prepare_geometry.py" --root "$root" --output "$out"
"$python" "$here/validate_region.py" --root "$root" --wizard "$1" --output "$out"
"$python" "$here/compare.py" --root "$root" --models "$demo_cache/models" --output "$out" --seed "${2:-0}" --candidates "${3:-16}" --profile cli
"$python" "$here/audit_pool.py" --root "$root" --output "$out" --seed "${2:-0}"
"$python" "$here/check_candidates.py" --root "$root" --output "$out"
printf 'Results: %s\n' "$out"
