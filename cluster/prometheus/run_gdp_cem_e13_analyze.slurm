#!/usr/bin/env bash
#SBATCH --job-name=gdp-e13-analyze
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-analyze-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-analyze-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E13 snapshot}"
: "${EVALUATION_JOB_ID:?missing E13 evaluation array job}"
: "${MANIFEST_JOB_ID:?missing E13 D4 manifest array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
OUT=${ROOT}/results/acid-alternative/gdp-cem-e13-d4/analysis/job-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e13_d4.py" \
  --root "${ROOT}" --evaluation-job-id "${EVALUATION_JOB_ID}" \
  --manifest-job-id "${MANIFEST_JOB_ID}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
printf '%s\n' 'study=gdp_cem_e13_d4_analysis' \
  "evaluation_job_id=${EVALUATION_JOB_ID}" "manifest_job_id=${MANIFEST_JOB_ID}" \
  "job_id=${SLURM_JOB_ID}" 'all_360_shards_complete_before_metric_read=true' \
  'd3_outcomes_read=false' 'protected_p4_c1_i1_read=false' > "${OUT}/audit.txt"
(cd "${OUT}" && sha256sum summary.json paired-outcomes.tsv \
  input-manifest.json audit.txt > sha256.txt)
chmod a-w "${OUT}"/* "${OUT}"
