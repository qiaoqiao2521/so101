#!/usr/bin/env bash
set -euo pipefail

demo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
demo_env="${SO101_DEMO_ENV:-${HOME}/.cache/so101-pretrained/venv}"
hf_cmd="${HF_BIN:-${HOME}/.local/bin/hf}"
task="${1:-push}"
seed="${2:-0}"
action_steps="${3:-10}"
case "${task}" in
  push|pick-place|bin-picking) ;;
  *) echo 'Usage: bash run.sh {push|pick-place|bin-picking} [seed=0] [action_steps=10]' >&2; exit 2 ;;
esac
if [[ ! "${seed}" =~ ^[0-9]+$ || ! "${action_steps}" =~ ^[0-9]+$ ]] ||
   (( 10#${action_steps} < 1 || 10#${action_steps} > 50 )); then
  echo 'Use a non-negative integer seed and action_steps from 1 to 50.' >&2
  exit 2
fi
if [[ ! -x "${demo_env}/bin/lerobot-eval" || ! -x "${hf_cmd}" ]]; then
  echo 'Run setup.sh and install the official Hugging Face CLI first.' >&2
  exit 1
fi
revision=cd6778d2cfa724c1bf5fc637490548e54d81dc4c
checkpoint="$("${hf_cmd}" download lerobot/smolvla_metaworld --revision "${revision}" --quiet)"
mkdir -p "${demo_root}/output"
run_dir="$(mktemp -d "${demo_root}/output/${task}-seed${seed}-steps${action_steps}-XXXXXX")"
printf 'model=lerobot/smolvla_metaworld\nrevision=%s\ntask=%s\nseed=%s\naction_steps=%s\n' \
  "${revision}" "${task}" "${seed}" "${action_steps}" > "${run_dir}/run.txt"
echo "Results: ${run_dir}"

# This runs only the official simulated Sawyer arm. No robot ports are accessed.
env -u HF_DEBUG MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MPLBACKEND=agg \
  "${demo_env}/bin/lerobot-eval" \
  "--policy.path=${checkpoint}" \
  --env.type=metaworld "--env.task=metaworld-${task}-v3" \
  --eval.batch_size=1 --eval.n_episodes=1 --eval.use_async_envs=false \
  --policy.device=cuda --policy.empty_cameras=2 \
  "--policy.n_action_steps=${action_steps}" \
  '--rename_map={"observation.image":"observation.images.camera1"}' \
  "--seed=${seed}" "--output_dir=${run_dir}" 2>&1 | tee "${run_dir}/eval.log"
echo "Inspect task success in ${run_dir}/eval_info.json and the generated videos."
