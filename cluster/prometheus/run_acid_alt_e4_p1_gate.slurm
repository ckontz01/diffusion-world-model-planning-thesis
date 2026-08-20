#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-p1-gate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-p1-gate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-p1-gate-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4 snapshot path}"
: "${TRAIN_JOB_ID:?submit with E4-P1 training array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
OUT=${ROOT}/results/acid-alternative/e4-p1-gate/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
arguments=()
for task_index in 0 1 2; do
  case "${task_index}" in
    0) TASK=pusht ;;
    1) TASK=reacher ;;
    2) TASK=cube ;;
  esac
  true_index=$((2 * task_index))
  shuffled_index=$((true_index + 1))
  arguments+=(
    --run "${TASK}=true_successor=${ROOT}/results/acid-alternative/e4-p1/${TASK}/true_successor/seed-7101-job-${TRAIN_JOB_ID}-${true_index}/summary.json"
    --run "${TASK}=shuffled_successor=${ROOT}/results/acid-alternative/e4-p1/${TASK}/shuffled_successor/seed-7101-job-${TRAIN_JOB_ID}-${shuffled_index}/summary.json"
  )
done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/aggregate_acid_alt_e4_p1.py" \
  "${arguments[@]}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUT}"
printf '%s\n' \
  "training_array=${TRAIN_JOB_ID}" \
  "gate_job_id=${SLURM_JOB_ID}" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/summary.json" \
  "${OUT}/runs.tsv" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
