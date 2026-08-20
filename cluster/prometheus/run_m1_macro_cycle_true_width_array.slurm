#!/usr/bin/env bash

#SBATCH --job-name=m1-pusht-widths
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --array=0-5%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m1-width-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m1-width-%A_%a.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/train_m1_macro_cycle_head.py"
LATENT_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-pusht-epoch15/p1-job-294589"
STATS_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596"
TARGET_DIR="${STABLEWM_HOME}/derived/m1-macro-targets/hi-lewm-pusht-epoch15/job-294613"
PAIR_DIR="${ROOT}/manifests/partitions/pusht-v1/scorer-pairs-seed-20260728"
CHECKPOINT_SHA256="b87805747d40037841877ce7b99b7dda3ebe7a52202c0ba46bf0006ab5d6f008"

SEEDS=(20260728 20260729 20260730)
if (( SLURM_ARRAY_TASK_ID < 3 )); then
  WIDTH=256
  SEED_INDEX="${SLURM_ARRAY_TASK_ID}"
else
  WIDTH=512
  SEED_INDEX="$((SLURM_ARRAY_TASK_ID - 3))"
fi
SEED="${SEEDS[SEED_INDEX]}"
OUTPUT_DIR="${STABLEWM_HOME}/runs/scorers/m1/pusht-v1/true-width${WIDTH}-seed${SEED}-job-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-m1-width-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

REQUIRED=(
  "${LATENT_DIR}/latents.h5"
  "${LATENT_DIR}/manifest.json"
  "${STATS_DIR}/stats.npz"
  "${STATS_DIR}/manifest.json"
  "${TARGET_DIR}/targets.h5"
  "${TARGET_DIR}/manifest.json"
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv"
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite M1 width output: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=m1_true_width_selection_on_p2"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "condition=true"
  echo "hidden_width=${WIDTH}"
  echo "training_seed=${SEED}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" \
    "${LATENT_DIR}/manifest.json" "${STATS_DIR}/manifest.json" \
    "${TARGET_DIR}/manifest.json" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED="'"${SEED}"'"
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
      --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
      --stats-npz "'"${STATS_DIR}"'/stats.npz" \
      --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --macro-target-h5 "'"${TARGET_DIR}"'/targets.h5" \
      --macro-target-manifest "'"${TARGET_DIR}"'/manifest.json" \
      --world-model-checkpoint-sha256 "'"${CHECKPOINT_SHA256}"'" \
      --output-dir "'"${OUTPUT_DIR}"'/run" \
      --condition true \
      --seed "'"${SEED}"'" \
      --hidden-width "'"${WIDTH}"'" \
      --device cuda \
      --learning-rate 0.0003 \
      --weight-decay 0.0001 \
      --batch-size 256 \
      --max-epochs 50 \
      --patience 10 \
      --min-delta 0.00000001
  '

test -s "${OUTPUT_DIR}/run/best-checkpoint.pt"
test -s "${OUTPUT_DIR}/run/training-result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
