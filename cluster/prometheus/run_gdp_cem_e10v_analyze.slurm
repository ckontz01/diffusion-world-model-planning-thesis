#!/usr/bin/env bash
#SBATCH --job-name=gdp-e10v-an
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e10v-an-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e10v-an-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E10V snapshot}"
: "${E10V_EVAL_JOB_ID:?missing E10V evaluation array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
tasks=(pusht reacher cube)
arguments=()
for index in 0 1 2; do
  task=${tasks[${index}]}
  arguments+=(--task-summary "${task}" "${ROOT}/results/acid-alternative/gdp-cem-e10v-p1/${task}/job-${E10V_EVAL_JOB_ID}-${index}/summary.json")
done
OUT=${ROOT}/results/acid-alternative/gdp-cem-e10v-p1/analysis/job-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e10v_p1.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E10V-PURE-VELOCITY-DIFFUSION-P1-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" "${arguments[@]}" \
  --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e10v_p1" "evaluation_array=${E10V_EVAL_JOB_ID}" \
  "analysis_job=${SLURM_JOB_ID}" "d2_read=false" "d3_read=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/manifest.json" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
