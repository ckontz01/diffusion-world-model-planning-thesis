#!/usr/bin/env bash

# Read-only, independent audit of all frozen PushT P2/P3 candidate executions.

#SBATCH --job-name=pusht-lineage-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-lineage-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-lineage-audit-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/audit_pusht_execution_lineage.py"
RUNNER="${ROOT}/scripts/run_audit_pusht_execution_lineage.slurm"
DATA="${ROOT}/data/stablewm"
OUTPUT_DIR="${DATA}/derived/lineage-audits/pusht-v1/execution-audit-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-pusht-lineage-audit-${SLURM_JOB_ID}"

P2_FIXED="${DATA}/derived/candidate-executions/pusht-v1/p2-stratum3-job-294652"
P2_REAL="${DATA}/derived/candidate-executions/pusht-v1/p2-real-frame-job-294659"
P3_FIXED="${DATA}/derived/candidate-executions/pusht-v1/p3-stratum3-job-295104"
P3_REAL="${DATA}/derived/candidate-executions/pusht-v1/p3-real-frame-job-295098"
DATASET="${DATA}/pusht_expert_train.h5"
PARTITIONS="${ROOT}/manifests/partitions/pusht-v1/episodes-seed-20260728.tsv"
STATS="${DATA}/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596/stats.npz"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}" "${PARTITIONS}" "${STATS}" \
  "${P2_FIXED}" "${P2_REAL}" "${P3_FIXED}" "${P3_REAL}"; do
  if [[ ! -e "${required}" ]]; then echo "Missing required input: ${required}" >&2; exit 2; fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=independent_pusht_execution_lineage_audit"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${PARTITIONS}" "${STATS}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --dataset "'"${DATASET}"'" \
      --partition-manifest "'"${PARTITIONS}"'" \
      --stats-npz "'"${STATS}"'" \
      --p2-fixed-root "'"${P2_FIXED}"'" \
      --p2-real-root "'"${P2_REAL}"'" \
      --p3-fixed-root "'"${P3_FIXED}"'" \
      --p3-real-root "'"${P3_REAL}"'" \
      --output-json "'"${OUTPUT_DIR}"'/audit.json"
  '

test -s "${OUTPUT_DIR}/audit.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
