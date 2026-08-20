#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-d2b-analyze
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2b-analyze-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2b-analyze-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4-D2B snapshot path}"
: "${D2A_SNAPSHOT:?submit with immutable E4-D2A snapshot path}"
: "${D2A_ANALYSIS_JOB_ID:?submit with passing E4-D2A analysis job ID}"
: "${EVAL_JOB_ID:?submit with completed E4-D2B array job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
D2A_ANALYSIS_DIR=${ROOT}/results/acid-alternative/e4-d2a/analysis/job-${D2A_ANALYSIS_JOB_ID}
ARMS=(
  b0 acid_l002 acid acid_l014 acid_flow acid_16_mean acid_16_min
  forward reachability deterministic_inverse gaussian_tail
  cider_tail_l002 cider_tail cider_tail_l014 cider_shuffled dide
  cider_raw cider_mean_violation
)
TASKS=(pusht reacher cube)
arguments=()
for task_index in 0 1 2; do
  task=${TASKS[${task_index}]}
  for arm_index in $(seq 0 17); do
    arm=${ARMS[${arm_index}]}
    array_index=$((task_index * 18 + arm_index))
    summary=${ROOT}/results/acid-alternative/e4-d2b/closed-loop/${task}/${arm}/planner-seed-8401-job-${EVAL_JOB_ID}-${array_index}/summary.json
    arguments+=(--run "${task}" "${arm}" "${summary}")
  done
done
OUT=${ROOT}/results/acid-alternative/e4-d2b/analysis/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_acid_alt_e4_d2b.py" \
  --parent-protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md" \
  --d2b-freeze "${SNAPSHOT}/ACID-ALTERNATIVE-E4-D2B-CLOSED-LOOP-FREEZE-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --d2a-implementation-freeze "${D2A_SNAPSHOT}/ACID-ALTERNATIVE-E4-D2A-IMPLEMENTATION-FREEZE-2026-08-16.md" \
  --d2a-source-manifest "${D2A_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --d2a-summary "${D2A_ANALYSIS_DIR}/summary.json" \
  --d2b-authorization "${D2A_ANALYSIS_DIR}/e4-d2b-authorization.json" \
  "${arguments[@]}" --output-dir "${OUT}"
printf '%s\n' \
  "status=ok" "study=e4_d2b_exploratory_closed_loop_analysis" \
  "eval_job_id=${EVAL_JOB_ID}" "d2a_analysis_job_id=${D2A_ANALYSIS_JOB_ID}" \
  "confirmation_claim_allowed=false" "alternative_to_acid_claim_allowed=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/summary.json" "${OUT}/manifest.json" "${OUT}/runs.tsv" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"

