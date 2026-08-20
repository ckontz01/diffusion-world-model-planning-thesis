#!/usr/bin/env bash

#SBATCH --job-name=selected-nulls
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --array=0-5%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/selected-null-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/selected-null-%A_%a.err

set -euo pipefail
: "${TRUE_SCORE_JOB_ID:?submit with TRUE_SCORE_JOB_ID set to the completed P2 true-scorer selection job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
STABLEWM_HOME="${ROOT}/data/stablewm"
M1_SCRIPT="${ROOT}/scripts/train_m1_macro_cycle_head.py"
M2_SCRIPT="${ROOT}/scripts/train_m2_diffusion_head.py"
SELECTION_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-true-selection-job-${TRUE_SCORE_JOB_ID}"
LATENT_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-pusht-epoch15/p1-job-294589"
STATS_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596"
TARGET_DIR="${STABLEWM_HOME}/derived/m1-macro-targets/hi-lewm-pusht-epoch15/job-294613"
PAIR_DIR="${ROOT}/manifests/partitions/pusht-v1/scorer-pairs-seed-20260728"
CHECKPOINT_SHA256="b87805747d40037841877ce7b99b7dda3ebe7a52202c0ba46bf0006ab5d6f008"

for required in \
  "${SELECTION_DIR}/scores.h5" \
  "${SELECTION_DIR}/manifest.json" \
  "${SELECTION_DIR}/checksums.sha256" \
  "${LATENT_DIR}/latents.h5" \
  "${LATENT_DIR}/manifest.json" \
  "${STATS_DIR}/stats.npz" \
  "${STATS_DIR}/manifest.json" \
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
(cd "${SELECTION_DIR}" && sha256sum -c checksums.sha256 >/dev/null)

M1_WIDTH=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["M1"]["selected_width"])' "${SELECTION_DIR}/manifest.json")
M2_WIDTH=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["M2"]["selected_width"])' "${SELECTION_DIR}/manifest.json")
M2_SIGMA=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["M2"]["selected_sigma"])' "${SELECTION_DIR}/manifest.json")
if [[ "${M1_WIDTH}" != "256" && "${M1_WIDTH}" != "512" ]]; then
  echo "Invalid selected M1 width: ${M1_WIDTH}" >&2
  exit 2
fi
if [[ "${M2_WIDTH}" != "512" && "${M2_WIDTH}" != "1024" ]]; then
  echo "Invalid selected M2 width: ${M2_WIDTH}" >&2
  exit 2
fi

SEEDS=(20260728 20260729 20260730)
if (( SLURM_ARRAY_TASK_ID < 3 )); then
  METHOD="M1"
  CONDITION="permuted"
  SEED_INDEX="${SLURM_ARRAY_TASK_ID}"
  WIDTH="${M1_WIDTH}"
  SCRIPT="${M1_SCRIPT}"
else
  METHOD="M2"
  CONDITION="mismatched"
  SEED_INDEX="$((SLURM_ARRAY_TASK_ID - 3))"
  WIDTH="${M2_WIDTH}"
  SCRIPT="${M2_SCRIPT}"
fi
SEED="${SEEDS[SEED_INDEX]}"
if [[ "${METHOD}" == "M1" ]]; then
  OUTPUT_DIR="${STABLEWM_HOME}/runs/scorers/m1/pusht-v1/permuted-width${WIDTH}-seed${SEED}-job-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
else
  OUTPUT_DIR="${STABLEWM_HOME}/derived/scorers/m2-diffusion-pusht-v1/mismatched/width-${WIDTH}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
fi
JOB_TMP="/tmp/ckontzias-selected-null-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite selected-null output: ${OUTPUT_DIR}" >&2
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
  echo "classification=selected_width_shuffled_or_mismatched_null"
  echo "selection_job_id=${TRUE_SCORE_JOB_ID}"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "method=${METHOD}"
  echo "condition=${CONDITION}"
  echo "hidden_width=${WIDTH}"
  echo "selected_m2_sigma=${M2_SIGMA}"
  echo "training_seed=${SEED}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" \
    "${SELECTION_DIR}/manifest.json" "${SELECTION_DIR}/checksums.sha256" \
    "${LATENT_DIR}/manifest.json" "${STATS_DIR}/manifest.json" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

if [[ "${METHOD}" == "M1" ]]; then
  for required in "${TARGET_DIR}/targets.h5" "${TARGET_DIR}/manifest.json"; do
    test -s "${required}"
  done
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
      python "'"${M1_SCRIPT}"'" \
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
        --condition permuted \
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
else
  apptainer exec --nv --cleanenv \
    --bind "${ROOT}:${ROOT}" \
    --bind "${JOB_TMP}:${JOB_TMP}" \
    "${IMAGE}" /bin/bash -c '
      set -euo pipefail
      export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
      export PYTHONNOUSERSITE=1
      export PYTHONHASHSEED="'"${SEED}"'"
      export CUBLAS_WORKSPACE_CONFIG=:4096:8
      export TMPDIR="'"${JOB_TMP}"'"
      python "'"${M2_SCRIPT}"'" \
        --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
        --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
        --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
        --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
        --stats-npz "'"${STATS_DIR}"'/stats.npz" \
        --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
        --output-dir "'"${OUTPUT_DIR}"'" \
        --condition mismatched \
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
  test -s "${OUTPUT_DIR}/best-checkpoint.pt"
  test -s "${OUTPUT_DIR}/training-result.json"
fi

echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
