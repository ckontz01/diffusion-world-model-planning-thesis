#!/usr/bin/env bash

#SBATCH --job-name=pusht-partitions
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-partitions-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-partitions-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/create_episode_partitions.py"
STABLEWM_HOME="${ROOT}/data/stablewm"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
OUTPUT_DIR="${ROOT}/manifests/partitions/pusht-v1"
OUTPUT_TSV="${OUTPUT_DIR}/episodes-seed-20260728.tsv"
OUTPUT_JSON="${OUTPUT_DIR}/episodes-seed-20260728-summary.json"
JOB_TMP="/tmp/ckontzias-pusht-partitions-${SLURM_JOB_ID}"

if [[ -e "${OUTPUT_TSV}" || -e "${OUTPUT_JSON}" ]]; then
  echo "Refusing to overwrite frozen partition files in ${OUTPUT_DIR}" >&2
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

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    python "'"${SCRIPT}"'" "'"${DATASET}"'" \
      --dataset-name pusht_expert_train \
      --seed 20260728 \
      --exclude-manifest "'"${STABLEWM_HOME}"'/repro/pusht_checkpoint_smoke/hi_pusht_checkpoint_smoke_results_episodes.tsv" \
      --exclude-manifest "'"${ROOT}"'/data/stablewm/repro/pusht_b0_b1_d25_seed42_job_294573/b0/b0_results_episodes.tsv" \
      --exclude-manifest "'"${ROOT}"'/data/stablewm/repro/pusht_b0_b1_d25_seed42_job_294575/b0/b0_results_episodes.tsv" \
      --output-tsv "'"${OUTPUT_TSV}"'" \
      --output-json "'"${OUTPUT_JSON}"'"
  '

sha256sum "${DATASET}" "${SCRIPT}" "${OUTPUT_TSV}" "${OUTPUT_JSON}"
