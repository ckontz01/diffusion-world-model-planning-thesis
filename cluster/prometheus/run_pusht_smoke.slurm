#!/usr/bin/env bash

#SBATCH --job-name=hi-lewm-pusht-smoke
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-smoke-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-py311-cu121"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
JOB_TMP="/tmp/ckontzias-hi-lewm-${SLURM_JOB_ID}"

if [[ "${JOB_TMP}" != "/tmp/ckontzias-hi-lewm-${SLURM_JOB_ID}" ]]; then
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
    cd "'"${CODE}"'"
    python - <<"PY"
import torch
print(f"torch={torch.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"cuda_available={torch.cuda.is_available()}")
print(f"gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}")
assert torch.cuda.is_available(), "CUDA is not available inside Apptainer"
PY
    bash scripts/run_pusht_smoke.sh
  '

echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Official Hi-LeWM PushT smoke workflow completed."
