#!/usr/bin/env bash

# Authorize D1 only when task B0 reproduction and native A1 gates both pass.

#SBATCH --job-name=acid-alt-task-r0-gate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:20:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-r0-gate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-r0-gate-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"; : "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"; : "${B0_JOB_ID:?submit with B0 R0 job ID}"; : "${SCORER_JOB_ID:?submit with core scorer job ID}"; : "${ACID_EVAL_JOB_ID:?submit with A1 R0 array ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"; IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; B0="${ROOT}/results/acid-alternative/r0/${TASK}/b0/planner-seed-42-job-${B0_JOB_ID}/summary.json"; OUTPUT_DIR="${ROOT}/results/acid-alternative/gates/${TASK}/r0-b0-acid-job-${SLURM_JOB_ID}"; OUTPUT="${OUTPUT_DIR}/gate.json"; SEEDS=(6101 6102 6103)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing existing output" >&2; exit 2; fi; mkdir -p "${OUTPUT_DIR}"
arguments=(--task "${TASK}" --b0-summary "${B0}" --source-manifest "${SOURCE_MANIFEST}" --output "${OUTPUT}")
for index in 0 1 2; do seed="${SEEDS[${index}]}"; arguments+=(--acid-summary "${ROOT}/results/acid-alternative/r0/${TASK}/acid/train-seed-${seed}-planner-seed-42-job-${ACID_EVAL_JOB_ID}-${index}/summary.json" --acid-training-summary "${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-${seed}-job-${SCORER_JOB_ID}-${index}/summary.json"); done
set +e; apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.aggregate_r0_gate "${arguments[@]}"; status=$?; set -e
printf '%s\n' "task=${TASK}" "b0_job_id=${B0_JOB_ID}" "scorer_job_id=${SCORER_JOB_ID}" "acid_eval_job_id=${ACID_EVAL_JOB_ID}" "gate_job_id=${SLURM_JOB_ID}" "gate_exit_status=${status}" > "${OUTPUT_DIR}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${OUTPUT}" "${OUTPUT_DIR}/provenance.txt" > "${OUTPUT_DIR}/sha256.txt"; exit "${status}"
