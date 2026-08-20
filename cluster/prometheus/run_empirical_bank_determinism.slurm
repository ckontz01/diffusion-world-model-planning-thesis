#!/usr/bin/env bash

# Build the released B1 empirical macro bank in two fresh Python processes and
# compare every stored array exactly. This isolates bank construction from CEM
# and environment execution.

#SBATCH --job-name=hi-lewm-bank-det
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/empirical-bank-det-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/empirical-bank-det-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
DIAGNOSTIC="${ROOT}/scripts/diagnose_empirical_bank.py"
OUTPUT="${STABLEWM_HOME}/repro/empirical_bank_determinism_job_${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-bank-det-${SLURM_JOB_ID}"

if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing to overwrite existing diagnostic: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

run_build() {
  local repetition="$1"
  apptainer exec --nv --cleanenv \
    --bind "${ROOT}:${ROOT}" \
    --bind "${JOB_TMP}:${JOB_TMP}" \
    "${IMAGE}" /bin/bash -c '
      set -euo pipefail
      export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
      export PYTHONNOUSERSITE=1
      export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
      export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
      export PYTHONHASHSEED=42
      export CUBLAS_WORKSPACE_CONFIG=:4096:8
      export EVAL_DETERMINISM=strict
      export TMPDIR="'"${JOB_TMP}"'"
      export MPLBACKEND=Agg
      export MUJOCO_GL=egl
      cd "'"${CODE}"'"
      python "'"${DIAGNOSTIC}"'" build \
        --code-root "'"${CODE}"'" \
        --stablewm-home "'"${STABLEWM_HOME}"'" \
        --policy runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \
        --seed 42 \
        --num-sequences 4096 \
        --output-json "'"${OUTPUT}"'/bank-'"${repetition}"'.json" \
        --output-npz "'"${OUTPUT}"'/bank-'"${repetition}"'.npz"
    '
}

echo "job_id=${SLURM_JOB_ID}"
echo "node=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
nvidia-smi
run_build 1
run_build 2

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
    python "'"${DIAGNOSTIC}"'" compare \
      "'"${OUTPUT}"'/bank-1.npz" \
      "'"${OUTPUT}"'/bank-2.npz" \
      --output-json "'"${OUTPUT}"'/comparison.json"
  '

sha256sum "${IMAGE}" "${DIAGNOSTIC}" > "${OUTPUT}/input-checksums.sha256"
find "${OUTPUT}" -type f ! -name output-checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT}/output-checksums.sha256"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
