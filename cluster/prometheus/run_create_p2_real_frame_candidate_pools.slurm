#!/usr/bin/env bash

#SBATCH --job-name=p2-real-pools
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-real-pools-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-real-pools-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/create_p2_real_frame_candidate_pools.py"
STABLEWM_HOME="${ROOT}/data/stablewm"
PARTITION_MANIFEST="${ROOT}/manifests/partitions/pusht-v1/episodes-seed-20260728.tsv"
LATENT_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-pusht-epoch15/p2-job-294590"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
OUTPUT_DIR="${STABLEWM_HOME}/derived/candidate-pools/pusht-v1/p2-real-frame-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p2-real-pools-${SLURM_JOB_ID}"

REQUIRED=(
  "${PARTITION_MANIFEST}"
  "${LATENT_DIR}/latents.h5"
  "${LATENT_DIR}/manifest.json"
  "${DATASET}"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite P2 real-frame pools: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

{
  echo "classification=p2_real_frame_candidate_pool_creation"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" "${PARTITION_MANIFEST}" \
    "${LATENT_DIR}/manifest.json"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --partition-manifest "'"${PARTITION_MANIFEST}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --dataset "'"${DATASET}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/candidate-pools.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --seed 20260728 \
      --pools-per-stratum 12 \
      --candidates-per-pool 64 \
      --delta 25
  '

test -s "${OUTPUT_DIR}/candidate-pools.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
