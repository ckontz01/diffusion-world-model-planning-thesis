#!/usr/bin/env bash

# Analyze per-task same-candidate physical-error rankings and null controls.

#SBATCH --job-name=acid-alt-task-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-audit-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${ANALYSIS_ROLE:?submit with ANALYSIS_ROLE=D1|C1}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${SCORE_JOB_ID:?submit with candidate-score job ID}"
: "${EXECUTION_JOB_ID:?submit with candidate-execution job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
[[ "${ANALYSIS_ROLE}" == D1 || "${ANALYSIS_ROLE}" == C1 ]] || { echo "invalid ANALYSIS_ROLE" >&2; exit 2; }
namespace="${ANALYSIS_ROLE,,}"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCORES="${ROOT}/results/acid-alternative/diagnostics/${TASK}/${namespace}-candidate-scores/job-${SCORE_JOB_ID}"
EXECUTIONS="${ROOT}/results/acid-alternative/diagnostics/${TASK}/${namespace}-candidate-executions/job-${EXECUTION_JOB_ID}"
OUTPUT="${ROOT}/results/acid-alternative/diagnostics/${TASK}/${namespace}-mechanism-audit/job-${SLURM_JOB_ID}"
for required in "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${IMAGE}" "${SCORES}/candidate-scores.pt" "${SCORES}/manifest.json" "${EXECUTIONS}/candidate-executions.h5" "${EXECUTIONS}/manifest.json"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}" \
  "${ENV_DIR}/bin/python" -m acid_alternative_diagnostics.analyze_candidate_audit \
  --score-artifact "${SCORES}/candidate-scores.pt" --score-manifest "${SCORES}/manifest.json" \
  --execution-h5 "${EXECUTIONS}/candidate-executions.h5" --execution-manifest "${EXECUTIONS}/manifest.json" \
  --analysis-role "${ANALYSIS_ROLE}" --bootstrap-seed $([[ "${ANALYSIS_ROLE}" == D1 ]] && echo 2026081301 || echo 2026081310) --bootstrap-repetitions 10000 --output-dir "${OUTPUT}"
printf '%s\n' "task=${TASK}" "analysis_role=${ANALYSIS_ROLE}" "score_job_id=${SCORE_JOB_ID}" "execution_job_id=${EXECUTION_JOB_ID}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  "${OUTPUT}/summary.json" "${OUTPUT}/pool-level-audit.tsv" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
