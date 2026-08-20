#!/usr/bin/env bash

#SBATCH --job-name=m1-target-full
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=01:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m1-target-full-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m1-target-full-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/extract_m1_macro_targets.py"
PAIR_DIR="${ROOT}/manifests/partitions/pusht-v1/scorer-pairs-seed-20260728"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15_object.ckpt"
OUTPUT_DIR="${STABLEWM_HOME}/derived/m1-macro-targets/hi-lewm-pusht-epoch15/job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m1-target-full-${SLURM_JOB_ID}"
DATASET_SHA256="b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb"

REQUIRED=(
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv"
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"
  "${DATASET}"
  "${CHECKPOINT}"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty required input: ${required}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite full M1 target output: ${OUTPUT_DIR}" >&2
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
  echo "classification=p1_frozen_m1_macro_target_extraction"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "dataset_verified_sha256=${DATASET_SHA256}"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json" "${CHECKPOINT}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm:'"${CODE}"'/scripts/diagnostics"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=20260728
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" \
      --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
      --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
      --dataset-file "'"${DATASET}"'" \
      --dataset-sha256 "'"${DATASET_SHA256}"'" \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --dataset-name pusht_expert_train \
      --policy runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \
      --checkpoint-file "'"${CHECKPOINT}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/targets.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --batch-size 4096 \
      --seed 20260728
  '

test -s "${OUTPUT_DIR}/targets.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
