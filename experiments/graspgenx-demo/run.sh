#!/usr/bin/env bash
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd -- "$here/../.." && pwd)"
demo_cache="${SO101_GRASPGENX_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/so101-graspgenx}"
python="$demo_cache/upstream/.venv/bin/python"
[[ -x "$python" ]] || { echo 'Run experiments/graspgenx-demo/setup.sh first.' >&2; exit 1; }
revision="$(git -C "$demo_cache/upstream" rev-parse HEAD)"
[[ "$revision" == b9429097728cb1c430dd78b92edf17ba318aad03 ]] || { echo 'Upstream revision mismatch.' >&2; exit 1; }
[[ -z "$(git -C "$demo_cache/upstream" status --porcelain --untracked-files=no)" ]] || { echo 'Upstream has tracked changes.' >&2; exit 1; }
out="$here/output/$(date +%Y%m%d-%H%M%S)-$$"
"$python" "$here/prepare_geometry.py" --root "$root" --output "$out"
"$python" "$here/infer.py" --models "$demo_cache/models" --output "$out" --seed "${1:-0}" --candidates "${2:-16}"
"$python" "$here/inspect_candidates.py" --root "$root" --output "$out" --seed "${1:-0}"
"$python" "$here/render_preview.py" "$out"
printf 'Results: %s\n' "$out"
