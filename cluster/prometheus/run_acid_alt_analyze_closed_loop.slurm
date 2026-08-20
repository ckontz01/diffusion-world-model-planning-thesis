#!/usr/bin/env bash

# Task-stratified paired analysis of the complete three-task development or C1 matrix.

#SBATCH --job-name=acid-alt-closed-loop
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-closed-loop-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-closed-loop-%j.err

set -euo pipefail
: "${ROLE:?submit with ROLE=development|confirmation}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${PUSHT_MATRIX_JOB_ID:?submit with PushT matrix array ID}"
: "${REACHER_MATRIX_JOB_ID:?submit with Reacher matrix array ID}"
: "${CUBE_MATRIX_JOB_ID:?submit with Cube matrix array ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
if [[ "${ROLE}" == development ]]; then namespace=d1; expected_starts=24; bootstrap_seed=2026081302; else namespace=c1; expected_starts=50; bootstrap_seed=2026081303; [[ "${ROLE}" == confirmation ]] || { echo "invalid ROLE" >&2; exit 2; }; fi
OUTPUT="${ROOT}/results/acid-alternative/analysis/${namespace}/closed-loop/job-${SLURM_JOB_ID}"
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
runs=()
tasks=(pusht reacher cube)
job_ids=("${PUSHT_MATRIX_JOB_ID}" "${REACHER_MATRIX_JOB_ID}" "${CUBE_MATRIX_JOB_ID}")
arms=(b0 acid reachability diffusion forward)
seeds=(6101 6102 6103)
planner_seeds=(7101 7102 7103)
for task_index in 0 1 2; do
  task="${tasks[${task_index}]}"; job_id="${job_ids[${task_index}]}"
  for arm_index in 0 1 2 3 4; do
    arm="${arms[${arm_index}]}"
    for seed_index in 0 1 2; do
      seed="${seeds[${seed_index}]}"; planner_seed="${planner_seeds[${seed_index}]}"; array_index=$((arm_index * 3 + seed_index))
      summary="${ROOT}/results/acid-alternative/${namespace}/${task}/${arm}/train-seed-${seed}-planner-seed-${planner_seed}-job-${job_id}-${array_index}/summary.json"
      test -f "${summary}"
      runs+=(--run "${task}=${arm}=${seed}=${summary}")
    done
  done
done
mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" \
  -m acid_alternative_diagnostics.analyze_closed_loop --role "${ROLE}" \
  --expected-starts "${expected_starts}" --bootstrap-seed "${bootstrap_seed}" \
  --bootstrap-repetitions 100000 --output-dir "${OUTPUT}" "${runs[@]}"
printf '%s\n' "role=${ROLE}" "pusht_job=${PUSHT_MATRIX_JOB_ID}" "reacher_job=${REACHER_MATRIX_JOB_ID}" \
  "cube_job=${CUBE_MATRIX_JOB_ID}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  "${OUTPUT}/summary.json" "${OUTPUT}/paired-outcomes.tsv" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
