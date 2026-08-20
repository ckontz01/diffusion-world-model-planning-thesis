#!/usr/bin/env bash

#SBATCH --job-name=m2-ae-selftest
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-ae-selftest-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-ae-selftest-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/train_m2_autoencoder_control.py"
OUTPUT_DIR="${ROOT}/data/stablewm/repro/m2-autoencoder-selftest-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m2-ae-selftest-${SLURM_JOB_ID}"

if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite autoencoder self-test output: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

{
  echo "classification=m2_autoencoder_control_self_test"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=123
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" --self-test > "'"${OUTPUT_DIR}"'/result.json"
  '

test -s "${OUTPUT_DIR}/result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
