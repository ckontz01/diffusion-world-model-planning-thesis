#!/usr/bin/env bash

# Execute all 24 x 300 frozen candidate trajectories in the real PushT simulator.

#SBATCH --job-name=acid-alt-pusht-d1-execute
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-execute-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-execute-%j.err

set -euo pipefail
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${CAPTURE_JOB_ID:?submit with candidate-capture job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
CORE_SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
CHECKPOINT="${STABLEWM_HOME}/pusht/lewm_hf_22b330c_object.ckpt"
CAPTURE="${ROOT}/results/acid-alternative/diagnostics/pusht/d1-b0-candidate-pools/planner-seed-7101-job-${CAPTURE_JOB_ID}"
OUTPUT="${ROOT}/results/acid-alternative/diagnostics/pusht/d1-candidate-executions/job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-d1-execute-${SLURM_JOB_ID}"

for required in \
  "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${SOURCE_MANIFEST}" "${IMAGE}" \
  "${DATASET}" "${CHECKPOINT}" "${CAPTURE}/candidate-pools.pt" \
  "${CAPTURE}/manifest.json"; do
  test -f "${required}"
done
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
sha256sum "$0" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${SOURCE_MANIFEST}" \
  > "${JOB_TMP}/source-provenance.sha256"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
nvidia-smi
apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONPATH="'"${DIAG_SNAPSHOT}"':'"${CORE_SNAPSHOT}"':'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export PYTHONHASHSEED=0
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export SLURM_JOB_ID="'"${SLURM_JOB_ID}"'"
    export TMPDIR="'"${JOB_TMP}"'"
    python -m acid_alternative_diagnostics.execute_candidate_pools \
      --candidate-artifact "'"${CAPTURE}"'/candidate-pools.pt" \
      --candidate-manifest "'"${CAPTURE}"'/manifest.json" \
      --code-root "'"${CODE}"'" \
      --eval-config-name pusht \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --dataset "'"${DATASET}"'" \
      --dataset-name pusht_expert_train \
      --world-model-policy pusht/lewm_hf_22b330c \
      --world-model-checkpoint "'"${CHECKPOINT}"'" \
      --source-manifest "'"${SOURCE_MANIFEST}"'" \
      --goal-offset 25 \
      --output-dir "'"${OUTPUT}"'"
  '
mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
sha256sum "${OUTPUT}/candidate-executions.h5" "${OUTPUT}/manifest.json" \
  "${OUTPUT}/source-provenance.sha256" > "${OUTPUT}/sha256.txt"
