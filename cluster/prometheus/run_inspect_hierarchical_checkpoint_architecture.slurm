#!/usr/bin/env bash

#SBATCH --job-name=hi-ckpt-arch
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/hi-ckpt-arch-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/hi-ckpt-arch-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
SCRIPT="${ROOT}/scripts/inspect_hierarchical_checkpoint_architecture.py"
RUNNER="${ROOT}/scripts/run_inspect_hierarchical_checkpoint_architecture.slurm"
BASE="${ROOT}/data/stablewm/pusht/lewm_object.ckpt"
HIERARCHICAL="${ROOT}/data/stablewm/runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15_object.ckpt"
OUTPUT_DIR="${ROOT}/manifests/checkpoints/pusht-hierarchical-architecture-job-${SLURM_JOB_ID}"
OUTPUT="${OUTPUT_DIR}/architecture.json"
JOB_TMP="/tmp/ckontzias-hi-ckpt-arch-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${BASE}" "${HIERARCHICAL}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing checkpoint inspection input: ${required}" >&2; exit 2; fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite checkpoint inspection" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=outcome_blind_released_checkpoint_architecture_inspection"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${SCRIPT}" "${RUNNER}" "${BASE}" "${HIERARCHICAL}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" --hierarchical "'"${HIERARCHICAL}"'" --base "'"${BASE}"'" --output "'"${OUTPUT}"'"
  '

test -s "${OUTPUT}"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
