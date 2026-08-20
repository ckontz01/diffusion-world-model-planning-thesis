#!/usr/bin/env bash

# Aggregate the development same-candidate mechanism audit.

#SBATCH --job-name=acid-alt-pusht-d1-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-audit-%j.err

set -euo pipefail
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${SCORE_JOB_ID:?submit with candidate-score job ID}"
: "${EXECUTION_JOB_ID:?submit with candidate-execution job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
CORE_SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCORES="${ROOT}/results/acid-alternative/diagnostics/pusht/d1-candidate-scores/job-${SCORE_JOB_ID}"
EXECUTIONS="${ROOT}/results/acid-alternative/diagnostics/pusht/d1-candidate-executions/job-${EXECUTION_JOB_ID}"
OUTPUT="${ROOT}/results/acid-alternative/diagnostics/pusht/d1-mechanism-audit/job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-d1-audit-${SLURM_JOB_ID}"

for required in \
  "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${IMAGE}" \
  "${SCORES}/candidate-scores.pt" "${SCORES}/manifest.json" \
  "${EXECUTIONS}/candidate-executions.h5" "${EXECUTIONS}/manifest.json"; do
  test -f "${required}"
done
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
sha256sum "$0" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  > "${JOB_TMP}/source-provenance.sha256"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
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
    export PYTHONPATH="'"${DIAG_SNAPSHOT}"':'"${CORE_SNAPSHOT}"'"
    export TMPDIR="'"${JOB_TMP}"'"
    python -m acid_alternative_diagnostics.analyze_candidate_audit \
      --score-artifact "'"${SCORES}"'/candidate-scores.pt" \
      --score-manifest "'"${SCORES}"'/manifest.json" \
      --execution-h5 "'"${EXECUTIONS}"'/candidate-executions.h5" \
      --execution-manifest "'"${EXECUTIONS}"'/manifest.json" \
      --bootstrap-seed 2026081301 \
      --bootstrap-repetitions 10000 \
      --output-dir "'"${OUTPUT}"'"
  '
mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
sha256sum "${OUTPUT}/summary.json" "${OUTPUT}/pool-level-audit.tsv" \
  "${OUTPUT}/source-provenance.sha256" > "${OUTPUT}/sha256.txt"
