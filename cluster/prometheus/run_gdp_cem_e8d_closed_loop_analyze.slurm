#!/usr/bin/env bash
#SBATCH --job-name=gdp-e8d-an
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e8d-an-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e8d-an-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E8D snapshot}"
: "${E8D_ARRAY_JOB_ID:?missing E8D evaluation array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
tasks=(pusht reacher cube)
arms=(b0 custom_b0 acid gaussian_refresh gadr_shuffled_refresh gadr_true_refresh gadr_true_first gaussian_select gadr_shuffled_select gadr_true_select)
arguments=()
for task_index in 0 1 2; do
  task=${tasks[${task_index}]}
  for arm_index in 0 1 2 3 4 5 6 7 8 9; do
    arm=${arms[${arm_index}]}
    array_index=$((task_index * 10 + arm_index))
    summary=${ROOT}/results/acid-alternative/gdp-cem-e8d-d2/${task}/${arm}/job-${E8D_ARRAY_JOB_ID}-${array_index}/summary.json
    arguments+=(--run "${task}" "${arm}" "${summary}")
  done
done
E8A=${ROOT}/results/acid-alternative/gdp-cem-e8a-refinement/analysis/job-297721/summary.json
OUT=${ROOT}/results/acid-alternative/gdp-cem-e8d-d2/analysis/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e8d_closed_loop.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E8D-GADR-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md" \
  --method-protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --e8a-aggregate "${E8A}" \
  "${arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e8d_exposed_d2" "evaluation_array=${E8D_ARRAY_JOB_ID}" \
  "analysis_job=${SLURM_JOB_ID}" "d2_read=true" "d3_read=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/manifest.json" "${OUT}/runs.tsv" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
