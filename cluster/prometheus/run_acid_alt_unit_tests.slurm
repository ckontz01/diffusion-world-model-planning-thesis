#!/usr/bin/env bash

#SBATCH --job-name=acid-alt-tests
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-tests-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-tests-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
JOB_TMP="/tmp/ckontzias-acid-alt-tests-${SLURM_JOB_ID}"

mkdir -p "${JOB_TMP}/apptainer"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONPATH="'"${SNAPSHOT}"':'"${CODE}"':'"${CODE}"'/third_party/lewm"
    cd "'"${SNAPSHOT}"'/acid_alternative"
    sha256sum -c ../SOURCE-MANIFEST.sha256
    python -m pytest tests -q
  '
