#!/usr/bin/env bash

# Submit only with an afterok dependency on the P1 latent-cache job and the
# M3 self-test job. Six tasks cover true/shuffled x three frozen seeds.

#SBATCH --job-name=m3-pusht-heads
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --array=0-5%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m3-train-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m3-train-%A_%a.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/train_m3_temporal_head.py"
LATENT_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-pusht-epoch15/p1-job-294589"
LATENT_H5="${LATENT_DIR}/latents.h5"
LATENT_MANIFEST="${LATENT_DIR}/manifest.json"
PAIR_DIR="${ROOT}/manifests/partitions/pusht-v1/scorer-pairs-seed-20260728"
PAIR_MANIFEST="${PAIR_DIR}/m3-balanced-delta1-40.tsv.gz"
PAIR_SUMMARY="${PAIR_DIR}/scorer-pair-manifests-summary.json"

SEEDS=(20260728 20260729 20260730)
if (( SLURM_ARRAY_TASK_ID < 3 )); then
  CONDITION="true"
  SEED_INDEX="${SLURM_ARRAY_TASK_ID}"
else
  CONDITION="shuffled"
  SEED_INDEX="$((SLURM_ARRAY_TASK_ID - 3))"
fi
TRAINING_SEED="${SEEDS[SEED_INDEX]}"
OUTPUT_DIR="${ROOT}/data/stablewm/derived/scorers/m3-trm-pusht-v1/${CONDITION}/seed-${TRAINING_SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-m3-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

for required in "${LATENT_H5}" "${LATENT_MANIFEST}" "${PAIR_MANIFEST}" "${PAIR_SUMMARY}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite existing M3 output: ${OUTPUT_DIR}" >&2
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
  echo "classification=m3_temporal_reachability_head"
  echo "condition=${CONDITION}"
  echo "training_seed=${TRAINING_SEED}"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" "${LATENT_MANIFEST}" \
    "${LATENT_DIR}/checksums.sha256" "${PAIR_MANIFEST}" "${PAIR_SUMMARY}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

nvidia-smi
apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED="'"${TRAINING_SEED}"'"
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --latent-h5 "'"${LATENT_H5}"'" \
      --latent-manifest "'"${LATENT_MANIFEST}"'" \
      --pair-manifest "'"${PAIR_MANIFEST}"'" \
      --pair-summary "'"${PAIR_SUMMARY}"'" \
      --output-dir "'"${OUTPUT_DIR}"'" \
      --condition "'"${CONDITION}"'" \
      --seed "'"${TRAINING_SEED}"'" \
      --device cuda
  '

test -s "${OUTPUT_DIR}/best-checkpoint.pt"
test -s "${OUTPUT_DIR}/training-result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
