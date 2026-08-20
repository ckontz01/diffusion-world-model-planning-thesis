#!/usr/bin/env bash
#SBATCH --job-name=acid-e3-d2-analysis
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e3-d2-analysis-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e3-d2-analysis-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E3 snapshot path}"
: "${AUTH_JOB_ID:?submit with completed E3 authorization job ID}"
: "${E3_ARRAY_JOB_ID:?submit with E3 closed-loop array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
AUTH=${ROOT}/results/acid-alternative/e3-d2-exploratory/authorization/job-${AUTH_JOB_ID}/authorization.json
OUT=${ROOT}/results/acid-alternative/e3-d2-exploratory/analysis/job-${SLURM_JOB_ID}

test -f "${AUTH}"
test ! -e "${OUT}"
tasks=(pusht reacher cube)
arms=(b0 acid forward rdx ae ae_shuffled)
arguments=()
for task_index in 0 1 2; do
  task=${tasks[${task_index}]}
  for arm_index in 0 1 2 3 4 5; do
    arm=${arms[${arm_index}]}
    for seed_offset in 0 1 2; do
      scorer_seed=$((6101 + seed_offset))
      planner_seed=$((8301 + seed_offset))
      array_index=$((task_index * 18 + arm_index * 3 + seed_offset))
      summary=${ROOT}/results/acid-alternative/e3-d2-exploratory/closed-loop/${task}/${arm}/scorer-seed-${scorer_seed}-planner-seed-${planner_seed}-job-${E3_ARRAY_JOB_ID}-${array_index}/summary.json
      arguments+=(--run "${task}" "${arm}" "${scorer_seed}" "${planner_seed}" "${summary}")
    done
  done
done

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_acid_alt_e3_d2_closed_loop.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --exploratory-authorization "${AUTH}" \
  "${arguments[@]}" --output-dir "${OUT}"

printf '%s\n' \
  "study=e3_exploratory_d2_closed_loop" \
  "e3_array=${E3_ARRAY_JOB_ID}" \
  "authorization_job=${AUTH_JOB_ID}" \
  "analysis_job_id=${SLURM_JOB_ID}" \
  "v3_stage_b_authorized=false" \
  "confirmation_claim_allowed=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/summary.json" \
  "${OUT}/manifest.json" \
  "${OUT}/runs.tsv" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
