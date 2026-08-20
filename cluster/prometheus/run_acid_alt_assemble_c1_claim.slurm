#!/usr/bin/env bash

# Final conservative claim decision from closed-loop, identification, and mechanism gates.

#SBATCH --job-name=acid-alt-c1-claim
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-c1-claim-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-c1-claim-%j.err

set -euo pipefail
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"; : "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"; : "${CLOSED_LOOP_JOB_ID:?submit with C1 closed-loop analysis ID}"; : "${VALIDATION_JOB_ID:?submit with C1 validation analysis ID}"; : "${MECHANISM_JOB_ID:?submit with three-task mechanism analysis ID}"; : "${CONFIRMATION_AUTHORIZATION:?submit with immutable C1 authorization}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; CLOSED="${ROOT}/results/acid-alternative/analysis/c1/closed-loop/job-${CLOSED_LOOP_JOB_ID}/summary.json"; VALIDATION="${ROOT}/results/acid-alternative/analysis/c1/validation-identification/job-${VALIDATION_JOB_ID}/summary.json"; MECHANISM="${ROOT}/results/acid-alternative/analysis/c1/mechanism/job-${MECHANISM_JOB_ID}/summary.json"; OUTPUT="${ROOT}/results/acid-alternative/analysis/c1/claim-decision/job-${SLURM_JOB_ID}"
for required in "${CLOSED}" "${VALIDATION}" "${MECHANISM}" "${CONFIRMATION_AUTHORIZATION}" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi; mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative_diagnostics.assemble_claim_gates --closed-loop "${CLOSED}" --validation "${VALIDATION}" --mechanism "${MECHANISM}" --confirmation-authorization "${CONFIRMATION_AUTHORIZATION}" --source-manifest "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUTPUT}"
printf '%s\n' "closed_loop_job=${CLOSED_LOOP_JOB_ID}" "validation_job=${VALIDATION_JOB_ID}" "mechanism_job=${MECHANISM_JOB_ID}" "authorization=${CONFIRMATION_AUTHORIZATION}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"; sha256sum "$0" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${CONFIRMATION_AUTHORIZATION}" "${OUTPUT}/summary.json" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
