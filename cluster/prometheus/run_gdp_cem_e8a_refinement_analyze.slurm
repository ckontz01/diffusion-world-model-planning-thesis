#!/usr/bin/env bash
#SBATCH --job-name=gdp-e8a-ref-an
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e8a-ref-an-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e8a-ref-an-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable GDP-CEM E8A snapshot}"
: "${REFINEMENT_ARRAY_JOB_ID:?missing E8A refinement array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
tasks=(pusht reacher cube)
arguments=()
for index in 0 1 2; do
  task=${tasks[${index}]}
  arguments+=(--task-summary "${task}" "${ROOT}/results/acid-alternative/gdp-cem-e8a-refinement/${task}/job-${REFINEMENT_ARRAY_JOB_ID}-${index}/summary.json")
done
OUT=${ROOT}/results/acid-alternative/gdp-cem-e8a-refinement/analysis/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e8a_refinement.py" \
  "${arguments[@]}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E8A-GAUSSIAN-ANCHORED-DIFFUSION-REFINEMENT-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e8a_refinement" "refinement_array_job=${REFINEMENT_ARRAY_JOB_ID}" \
  "analysis_job=${SLURM_JOB_ID}" "d2_read=false" "d3_read=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"

