#!/usr/bin/env bash

# Submit only with afterok dependencies on the P1 statistics and M2 self-test.

#SBATCH --job-name=m2-real-smoke
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-real-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-real-smoke-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/train_m2_diffusion_head.py"
LATENT_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-pusht-epoch15/p1-job-294589"
PAIR_DIR="${ROOT}/manifests/partitions/pusht-v1/scorer-pairs-seed-20260728"
STATS_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596"
OUTPUT_DIR="${ROOT}/data/stablewm/repro/m2-real-smoke-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m2-smoke-${SLURM_JOB_ID}"

REQUIRED=(
  "${LATENT_DIR}/latents.h5"
  "${LATENT_DIR}/manifest.json"
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv"
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"
  "${STATS_DIR}/stats.npz"
  "${STATS_DIR}/manifest.json"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite existing smoke output: ${OUTPUT_DIR}" >&2
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
  echo "classification=m2_real_data_development_smoke"
  echo "condition=true"
  echo "training_seed=20260728"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" \
    "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json" \
    "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json"
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
    export PYTHONHASHSEED=20260728
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
      --condition true \
      --seed 20260728 \
      --hidden-width 512 \
      --max-epochs 1 \
      --train-pair-limit 8192 \
      --validation-pair-limit 2048 \
      --smoke \
      --device cuda
  '

test -s "${OUTPUT_DIR}/best-checkpoint.pt"
test -s "${OUTPUT_DIR}/training-result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
