#!/usr/bin/env bash

#SBATCH --job-name=m2-ae-selected
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --array=0-2%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-ae-selected-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-ae-selected-%A_%a.err

set -euo pipefail
: "${TRUE_SCORE_JOB_ID:?submit with TRUE_SCORE_JOB_ID set to the completed P2 true-scorer selection job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/train_m2_autoencoder_control.py"
SELECTION_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-true-selection-job-${TRUE_SCORE_JOB_ID}"
SELFTEST_DIR="${STABLEWM_HOME}/repro/m2-autoencoder-selftest-job-294695"
LATENT_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-pusht-epoch15/p1-job-294589"
STATS_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596"
PAIR_DIR="${ROOT}/manifests/partitions/pusht-v1/scorer-pairs-seed-20260728"

for required in \
  "${SELECTION_DIR}/manifest.json" \
  "${SELECTION_DIR}/checksums.sha256" \
  "${SELFTEST_DIR}/result.json" \
  "${SELFTEST_DIR}/checksums.sha256" \
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
(cd "${SELFTEST_DIR}" && sha256sum -c checksums.sha256 >/dev/null)

WIDTH=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["M2"]["selected_width"])' "${SELECTION_DIR}/manifest.json")
if [[ "${WIDTH}" != "512" && "${WIDTH}" != "1024" ]]; then
  echo "Invalid selected M2 width: ${WIDTH}" >&2
  exit 2
fi
SEEDS=(20260728 20260729 20260730)
SEED="${SEEDS[SLURM_ARRAY_TASK_ID]}"
OUTPUT_DIR="${STABLEWM_HOME}/derived/scorers/m2-autoencoder-pusht-v1/width-${WIDTH}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-m2-ae-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite M2 autoencoder output: ${OUTPUT_DIR}" >&2
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
  echo "classification=m2_autoencoder_control_training"
  echo "selection_job_id=${TRUE_SCORE_JOB_ID}"
  echo "self_test_job_id=294695"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "hidden_width=${WIDTH}"
  echo "training_seed=${SEED}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" \
    "${SELECTION_DIR}/manifest.json" "${SELECTION_DIR}/checksums.sha256" \
    "${SELFTEST_DIR}/result.json" "${SELFTEST_DIR}/checksums.sha256" \
    "${LATENT_DIR}/manifest.json" "${STATS_DIR}/manifest.json" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
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
      --output-dir "'"${OUTPUT_DIR}"'" \
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
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
