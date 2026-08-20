#!/usr/bin/env bash
#SBATCH --job-name=acid-e6d-analysis
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6d-analysis-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6d-analysis-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing E6D snapshot}"
: "${AUTH_JOB_ID:?missing authorization job}"
: "${E6D_ARRAY_JOB_ID:?missing E6D array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
AUTH=${ROOT}/results/acid-alternative/e6d-allgate-controls/authorization/job-${AUTH_JOB_ID}/authorization.json
OUT=${ROOT}/results/acid-alternative/e6d-allgate-controls/analysis/job-${SLURM_JOB_ID}
tasks=(pusht reacher cube)
new_arms=(rdx_shuffled_gate_all_q40 forward_gate_all_q40 acid_gate_all_q40)
arguments=()
for task_index in 0 1 2; do
  task=${tasks[${task_index}]}
  e6_base=$((task_index * 10))
  arguments+=(--anchor "${task}" acid_cont "${ROOT}/results/acid-alternative/e6-d2-quantile/closed-loop/${task}/acid_cont/seed-6101-8301-job-297656-$((e6_base + 1))/summary.json")
  arguments+=(--anchor "${task}" rdx_gate_all_q40 "${ROOT}/results/acid-alternative/e6-d2-quantile/closed-loop/${task}/rdx_gate_all_q40/seed-6101-8301-job-297656-$((e6_base + 6))/summary.json")
  for arm_index in 0 1 2; do
    arm=${new_arms[${arm_index}]}
    array_index=$((task_index * 3 + arm_index))
    arguments+=(--run "${task}" "${arm}" "${ROOT}/results/acid-alternative/e6d-allgate-controls/closed-loop/${task}/${arm}/job-${E6D_ARRAY_JOB_ID}-${array_index}/summary.json")
  done
done
test ! -e "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_acid_alt_e6d_d2.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E6D-ALL-ITERATIONS-MATCHED-CONTROLS-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --authorization "${AUTH}" \
  --e6-summary "${ROOT}/results/acid-alternative/e6-d2-quantile/analysis/job-297657/summary.json" \
  "${arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "study=e6d_allgate_controls" "array_job=${E6D_ARRAY_JOB_ID}" "analysis_job=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
