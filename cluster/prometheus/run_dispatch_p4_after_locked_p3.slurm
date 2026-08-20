#!/usr/bin/env bash

# One-shot mechanical dispatcher. Submit with dependency afterok:295115.

#SBATCH --job-name=p4-gate-dispatch
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:10:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-gate-dispatch-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p4-gate-dispatch-%j.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SCRIPT="${ROOT}/scripts/dispatch_p4_after_locked_p3.py"
RUNNER="${ROOT}/scripts/run_dispatch_p4_after_locked_p3.slurm"
OUTPUT_DIR="${ROOT}/data/stablewm/derived/closed-loop-confirmation/pusht-v1/dispatch-p3-job-295115"

for required in "${SCRIPT}" "${RUNNER}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing dispatcher input: ${required}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing duplicate P4 dispatch; receipt directory already exists: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}"

{
  echo "classification=p4_dispatch_from_locked_p3_promotion"
  echo "job_id=${SLURM_JOB_ID}"
  echo "dependency_expected=afterok:295115"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${SCRIPT}" "${RUNNER}"
} > "${OUTPUT_DIR}/provenance.txt"

/usr/bin/python3 "${SCRIPT}" --output-json "${OUTPUT_DIR}/dispatch.json"

test -s "${OUTPUT_DIR}/dispatch.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
