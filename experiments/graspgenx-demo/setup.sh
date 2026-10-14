#!/usr/bin/env bash
set -euo pipefail
demo_cache="${SO101_GRASPGENX_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/so101-graspgenx}"
upstream="$demo_cache/upstream"
revision=b9429097728cb1c430dd78b92edf17ba318aad03
mkdir -p "$demo_cache"
if [[ ! -d "$upstream/.git" ]]; then
  git -c http.version=HTTP/1.1 clone --no-checkout https://github.com/NVlabs/GraspGenX.git "$upstream"
  git -C "$upstream" -c http.version=HTTP/1.1 checkout --detach "$revision"
fi
if [[ "$(git -C "$upstream" rev-parse HEAD)" != "$revision" ]]; then
  if [[ -n "$(git -C "$upstream" status --porcelain --untracked-files=no)" ]]; then
    echo 'Cached upstream has tracked edits; preserve them before changing revision.' >&2
    exit 1
  fi
  git -C "$upstream" -c http.version=HTTP/1.1 checkout --detach "$revision"
fi
uv venv --python 3.11 --allow-existing "$upstream/.venv"
# Official sweep-volume construction imports the lightweight serving types.
uv pip install --python "$upstream/.venv/bin/python" --torch-backend cu124 -e "${upstream}[serve]"
# Existing SO101 motion, localization imports and MP4 output in this isolated environment.
uv pip install --python "$upstream/.venv/bin/python" ompl==2.0.1 \
  imageio-ffmpeg==0.6.0 opencv-python-headless==4.11.0.86 \
  mujoco==3.15.0 python-fcl==0.7.0.11 rtree==1.4.1
HF_HUB_DISABLE_XET=1 hf download adithyamurali/GraspGenXModel \
  release/gen/config.yaml release/gen/epoch_736.pth \
  release/dis/config.yaml release/dis/epoch_1056.pth README.md \
  --revision 7c834043c11a11417e31d6d5ea9355801e40a2c1 \
  --local-dir "$demo_cache/models"
printf 'Ready: %s\n' "$upstream/.venv/bin/python"
