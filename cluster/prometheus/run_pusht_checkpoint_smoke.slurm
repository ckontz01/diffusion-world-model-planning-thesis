#!/usr/bin/env bash

# Evaluate the released epoch-15 Hi-LeWM checkpoint with the same reduced
# evaluator settings as the artifact smoke workflow. This bypasses only the
# broken training entry point in the released package.

#SBATCH --job-name=hi-lewm-ckpt-smoke
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-ckpt-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-ckpt-smoke-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
OUTPUT_ROOT="${STABLEWM_HOME}/repro/pusht_checkpoint_smoke"
RESULT_FILE="${OUTPUT_ROOT}/hi_pusht_checkpoint_smoke_results.txt"
JOB_TMP="/tmp/ckontzias-hi-lewm-ckpt-${SLURM_JOB_ID}"

if [[ -e "${RESULT_FILE}" ]]; then
  echo "Refusing to overwrite existing smoke result: ${RESULT_FILE}" >&2
  exit 2
fi
if [[ "${JOB_TMP}" != "/tmp/ckontzias-hi-lewm-ckpt-${SLURM_JOB_ID}" ]]; then
  echo "Unexpected job scratch path: ${JOB_TMP}" >&2
  exit 2
fi

mkdir -p "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

echo "job_id=${SLURM_JOB_ID}"
echo "node=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
nvidia-smi

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export TMPDIR="'"${JOB_TMP}"'"
    export MPLBACKEND=Agg
    export MUJOCO_GL=egl
    export SDL_VIDEODRIVER=dummy
    export HYDRA_FULL_ERROR=1
    cd "'"${CODE}"'"
    python - <<"PY"
import torch
import importlib.metadata as metadata
swm_version = metadata.version("stable-worldmodel")
print(f"torch={torch.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"cuda_available={torch.cuda.is_available()}")
print(f"gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}")
print(f"stable_worldmodel={swm_version}")
assert torch.cuda.is_available(), "CUDA is not available inside Apptainer"
assert swm_version == "0.0.6"
PY
    python -m h_le_wm.eval.hierarchical \
      --config-name=hi_pusht \
      policy=runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \
      seed=42 \
      planning.mode=hierarchical \
      eval.num_eval=8 \
      eval.goal_offset_steps=25 \
      eval.eval_budget=25 \
      planning.high.solver.device=cuda \
      planning.low.solver.device=cuda \
      solver.device=cuda \
      planning.high.solver.num_samples=64 \
      planning.high.solver.n_steps=5 \
      planning.high.solver.topk=4 \
      planning.high.plan_config.horizon=2 \
      planning.high.plan_config.receding_horizon=1 \
      planning.high.replan_interval=5 \
      planning.low.solver.num_samples=64 \
      planning.low.solver.n_steps=10 \
      planning.low.solver.topk=8 \
      planning.low.plan_config.horizon=5 \
      planning.low.plan_config.receding_horizon=1 \
      output.subdir=. \
      output.filename=hi_pusht_checkpoint_smoke_results.txt \
      +output.root_dir="'"${OUTPUT_ROOT}"'"
  '

test -s "${RESULT_FILE}"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Released-checkpoint Hi-LeWM PushT smoke evaluation completed."
