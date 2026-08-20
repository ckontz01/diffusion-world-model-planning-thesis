#!/usr/bin/env bash

# P1-only zero-source companion training: PushT and TwoRoom x three frozen seeds.

#SBATCH --job-name=m2v2-uncond
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --array=0-5%3
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2v2-uncond-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2v2-uncond-%A_%a.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/train_m2v2_unconditional_head.py"
BASE_SCRIPT="${ROOT}/scripts/train_m2_diffusion_head.py"
RUNNER="${ROOT}/scripts/run_train_m2v2_unconditional_array.slurm"
SPEC="${ROOT}/protocol/M2V2-P1-P2-FEASIBILITY-SPEC-2026-08-12.md"
: "${SPEC_SHA256:?submit with frozen SPEC_SHA256}"

SEEDS=(20260728 20260729 20260730)
environment_index=$((SLURM_ARRAY_TASK_ID / 3))
seed_index=$((SLURM_ARRAY_TASK_ID % 3))
seed="${SEEDS[seed_index]}"
if (( environment_index == 0 )); then
  ENVIRONMENT="pusht"
  LATENT_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-pusht-epoch15/p1-job-294589"
  STATS_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596"
  PAIR_DIR="${ROOT}/manifests/partitions/pusht-v1/scorer-pairs-seed-20260728"
  DATASET_NAMESPACE="pusht_expert_train"
else
  ENVIRONMENT="tworoom"
  LATENT_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-tworoom-epoch15/p1"
  STATS_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-tworoom-epoch15/p1-train-stats"
  PAIR_DIR="${ROOT}/manifests/partitions/tworoom-v1/scorer-pairs-seed-20260728"
  DATASET_NAMESPACE="tworoom"
fi
OUTPUT_DIR="${ROOT}/data/stablewm/derived/scorers/m2v2-unconditional-${ENVIRONMENT}-v1/width-1024/seed-${seed}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-m2v2-uncond-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${BASE_SCRIPT}" "${RUNNER}" "${SPEC}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" \
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"; do
  if [[ ! -s "${required}" ]]; then echo "Missing M2v2 training input: ${required}" >&2; exit 2; fi
done
echo "${SPEC_SHA256}  ${SPEC}" | sha256sum -c - >/dev/null
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite M2v2 training output" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=${ENVIRONMENT}_m2v2_unconditional_p1_training"
  echo "partition=P1-only"
  echo "source_mode=hard_zero_every_call"
  echo "hidden_width=1024"
  echo "training_seed=${seed}"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${BASE_SCRIPT}" "${RUNNER}" "${SPEC}" \
    "${LATENT_DIR}/manifest.json" "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED="'"${seed}"'"
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
      --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
      --stats-npz "'"${STATS_DIR}"'/stats.npz" \
      --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --output-dir "'"${OUTPUT_DIR}"'" --condition true \
      --dataset-hash-namespace "'"${DATASET_NAMESPACE}"'" \
      --seed "'"${seed}"'" --hidden-width 1024 --device cuda
  '

test -s "${OUTPUT_DIR}/best-checkpoint.pt"
test -s "${OUTPUT_DIR}/training-result.json"
grep -q '"method": "M2v2_unconditional_epsilon_prediction"' "${OUTPUT_DIR}/training-result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
