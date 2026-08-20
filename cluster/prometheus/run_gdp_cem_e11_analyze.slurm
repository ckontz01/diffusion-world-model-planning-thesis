#!/usr/bin/env bash
#SBATCH --job-name=gdp-e11-analyze
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e11-analyze-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e11-analyze-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E11 snapshot}"
: "${EVALUATION_JOB_ID:?missing E11 evaluation array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
OUT=${ROOT}/results/acid-alternative/gdp-cem-e11-d3/analysis/job-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e11_d3.py" \
  --root "${ROOT}" --evaluation-job-id "${EVALUATION_JOB_ID}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e11_d3_analysis" "evaluation_job_id=${EVALUATION_JOB_ID}" \
  "job_id=${SLURM_JOB_ID}" "all_shards_complete_before_read=true" \
  "protected_c1_i1_read=false" > "${OUT}/audit.txt"
sha256sum "${OUT}/summary.json" "${OUT}/paired-outcomes.tsv" \
  "${OUT}/input-manifest.json" "${OUT}/audit.txt" > "${OUT}/sha256.txt"
