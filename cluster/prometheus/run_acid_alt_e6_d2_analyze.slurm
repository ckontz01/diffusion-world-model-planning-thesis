#!/usr/bin/env bash
#SBATCH --job-name=acid-e6-analysis
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6-analysis-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6-analysis-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E6 snapshot path}"
: "${AUTH_JOB_ID:?missing E6 authorization job}"
: "${E6_ARRAY_JOB_ID:?missing E6 array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
AUTH=${ROOT}/results/acid-alternative/e6-d2-quantile/authorization/job-${AUTH_JOB_ID}/authorization.json
OUT=${ROOT}/results/acid-alternative/e6-d2-quantile/analysis/job-${SLURM_JOB_ID}
tasks=(pusht reacher cube)
arms=(b0 acid_cont forward_cont rdx_cont rdx_gate_tail5_q20 rdx_gate_tail5_q40 rdx_gate_all_q40 rdx_shuffled_gate_tail5_q40 acid_gate_tail5_q40 forward_gate_tail5_q40)
arguments=()
for task_index in 0 1 2; do
  task=${tasks[${task_index}]}
  for arm_index in 0 1 2 3 4 5 6 7 8 9; do
    arm=${arms[${arm_index}]}
    array_index=$((task_index * 10 + arm_index))
    summary=${ROOT}/results/acid-alternative/e6-d2-quantile/closed-loop/${task}/${arm}/seed-6101-8301-job-${E6_ARRAY_JOB_ID}-${array_index}/summary.json
    arguments+=(--run "${task}" "${arm}" "${summary}")
  done
done
test ! -e "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_acid_alt_e6_d2.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E6-QUANTILE-CONSTRAINED-CEM-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --authorization "${AUTH}" \
  "${arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "study=e6_exposed_d2_quantile" "array_job=${E6_ARRAY_JOB_ID}" "analysis_job=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/runs.tsv" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
