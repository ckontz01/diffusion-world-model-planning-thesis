#!/usr/bin/env bash

#SBATCH --job-name=pusht-h5-inspect
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-h5-inspect-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-h5-inspect-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/inspect_hdf5_dataset.py"
DATASET="${ROOT}/data/stablewm/pusht_expert_train.h5"
OUTPUT="${ROOT}/manifests/pusht-dataset-inspection-job-${SLURM_JOB_ID}.json"
JOB_TMP="/tmp/ckontzias-pusht-inspect-${SLURM_JOB_ID}"

mkdir -p "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" "'"${DATASET}"'" --output-json "'"${OUTPUT}"'"
  '

sha256sum "${DATASET}" "${SCRIPT}" "${OUTPUT}"

