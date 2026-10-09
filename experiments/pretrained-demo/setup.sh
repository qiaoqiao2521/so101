#!/usr/bin/env bash
set -euo pipefail

# Keep pretrained inference separate from the existing SO101 learning environment.
demo_env="${SO101_DEMO_ENV:-${HOME}/.cache/so101-pretrained/venv}"
uv_cmd="${UV_BIN:-${HOME}/.local/bin/uv}"
if [[ ! -x "${demo_env}/bin/python" ]]; then
  "${uv_cmd}" venv --python 3.12 "${demo_env}"
fi
"${uv_cmd}" pip install --python "${demo_env}/bin/python" \
  'lerobot[smolvla,metaworld,evaluation]==0.6.1' \
  'torch==2.7.1' 'torchvision==0.22.1' --torch-backend cu126
