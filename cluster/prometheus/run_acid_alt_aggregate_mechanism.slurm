#!/usr/bin/env bash

# Equal-task-weight aggregate of three frozen D1 or C1 mechanism audits.

#SBATCH --job-name=acid-alt-mechanism-all
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-mechanism-all-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-mechanism-all-%j.err

set -euo pipefail
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${ANALYSIS_ROLE:?submit with ANALYSIS_ROLE=D1|C1}"
: "${PUSHT_AUDIT_JOB_ID:?submit with PushT audit job ID}"
: "${REACHER_AUDIT_JOB_ID:?submit with Reacher audit job ID}"
: "${CUBE_AUDIT_JOB_ID:?submit with Cube audit job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
[[ "${ANALYSIS_ROLE}" == D1 || "${ANALYSIS_ROLE}" == C1 ]] || { echo "invalid ANALYSIS_ROLE" >&2; exit 2; }
namespace="${ANALYSIS_ROLE,,}"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
PUSHT="${ROOT}/results/acid-alternative/diagnostics/pusht/${namespace}-mechanism-audit/job-${PUSHT_AUDIT_JOB_ID}/summary.json"
REACHER="${ROOT}/results/acid-alternative/diagnostics/reacher/${namespace}-mechanism-audit/job-${REACHER_AUDIT_JOB_ID}/summary.json"
CUBE="${ROOT}/results/acid-alternative/diagnostics/cube/${namespace}-mechanism-audit/job-${CUBE_AUDIT_JOB_ID}/summary.json"
OUTPUT="${ROOT}/results/acid-alternative/analysis/${namespace}/mechanism/job-${SLURM_JOB_ID}"
for required in "${PUSHT}" "${REACHER}" "${CUBE}" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" \
  -m acid_alternative_diagnostics.aggregate_mechanism_audits \
  --audit "pusht=${PUSHT}" --audit "reacher=${REACHER}" --audit "cube=${CUBE}" \
  --analysis-role "${ANALYSIS_ROLE}" \
  --source-manifest "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --bootstrap-seed $([[ "${ANALYSIS_ROLE}" == D1 ]] && echo 2026081309 || echo 2026081311) --bootstrap-repetitions 100000 --output-dir "${OUTPUT}"
printf '%s\n' "analysis_role=${ANALYSIS_ROLE}" "pusht_audit=${PUSHT_AUDIT_JOB_ID}" "reacher_audit=${REACHER_AUDIT_JOB_ID}" \
  "cube_audit=${CUBE_AUDIT_JOB_ID}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  "${OUTPUT}/summary.json" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
