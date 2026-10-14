#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd -- "$here/../.." && pwd)"
demo_cache="${SO101_GRASPGENX_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/so101-graspgenx}"
python="$demo_cache/upstream/.venv/bin/python"
[[ -x "$python" ]] || { echo 'Run experiments/graspgenx-demo/setup.sh first.' >&2; exit 1; }
[[ "$(git -C "$demo_cache/upstream" rev-parse HEAD)" == b9429097728cb1c430dd78b92edf17ba318aad03 ]] || { echo 'Upstream revision mismatch.' >&2; exit 1; }
[[ -z "$(git -C "$demo_cache/upstream" status --porcelain --untracked-files=no)" ]] || { echo 'Upstream has tracked changes.' >&2; exit 1; }
out="$here/output/comparison-$(date +%Y%m%d-%H%M%S)-$$"
export MUJOCO_GL=egl
"$python" "$here/prepare_geometry.py" --root "$root" --output "$out"
"$python" "$here/compare.py" --root "$root" --models "$demo_cache/models" --output "$out" --seed "${1:-0}" --candidates "${2:-16}" --profile "${3:-cli}"
printf 'Results: %s\n' "$out"
