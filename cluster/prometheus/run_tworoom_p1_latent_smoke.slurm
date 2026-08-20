#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p1-latent-smoke
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p1-latent-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p1-latent-smoke-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/extract_frozen_latents.py"
RUNNER="${ROOT}/scripts/run_tworoom_p1_latent_smoke.slurm"
CONFIG="${CODE}/config/eval/hi_tworoom.yaml"
DATASET="${STABLEWM_HOME}/tworoom.h5"
PARTITIONS="${ROOT}/manifests/partitions/tworoom-v1/episodes-seed-20260728.tsv"
CHECKPOINT="${STABLEWM_HOME}/runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15_object.ckpt"
OUTPUT_DIR="${STABLEWM_HOME}/repro/tworoom-p1-latent-smoke-job-${SLURM_JOB_ID}"
OUTPUT_H5="${OUTPUT_DIR}/latents.h5"
OUTPUT_JSON="${OUTPUT_DIR}/manifest.json"
JOB_TMP="/tmp/ckontzias-tworoom-p1-latent-smoke-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="65a4b66265ad31dc0c6e4539ba42498a2618ede6e1dd75cf12e206a9a1c69fee"
EXPECTED_CONFIG_SHA256="13d671d15f31093c623d1e6d4d4448ce2f51bb7c81504dfc225aa48e17ec8da1"
EXPECTED_DATASET_SHA256="129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623"
EXPECTED_PARTITIONS_SHA256="47971097b1979798345c298d91eb36f91a0884353789b7f8736e6a1f9e79f790"
EXPECTED_CHECKPOINT_SHA256="5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${CONFIG}" "${DATASET}" \
  "${PARTITIONS}" "${CHECKPOINT}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom latent-smoke input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_CONFIG_SHA256}  ${CONFIG}" | sha256sum -c -
echo "${EXPECTED_DATASET_SHA256}  ${DATASET}" | sha256sum -c -
echo "${EXPECTED_PARTITIONS_SHA256}  ${PARTITIONS}" | sha256sum -c -
echo "${EXPECTED_CHECKPOINT_SHA256}  ${CHECKPOINT}" | sha256sum -c -
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite TwoRoom latent smoke" >&2; exit 2; fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p1_frozen_latent_implementation_smoke"
  echo "excluded_from_scientific_results=true"
  echo "episode_limit=2"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${CONFIG}" "${DATASET}" \
    "${PARTITIONS}" "${CHECKPOINT}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=42
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export EVAL_DETERMINISM=strict
    export TMPDIR="'"${JOB_TMP}"'"
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" \
      --code-root "'"${CODE}"'" \
      --eval-config-dir "'"${CODE}"'/config/eval" --eval-config-name hi_tworoom \
      --stablewm-home "'"${STABLEWM_HOME}"'" --dataset "'"${DATASET}"'" \
      --partition-manifest "'"${PARTITIONS}"'" --partition P1 \
      --policy runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15 \
      --checkpoint-file "'"${CHECKPOINT}"'" --seed 42 --batch-size 128 \
      --episode-limit 2 --output-h5 "'"${OUTPUT_H5}"'" \
      --output-json "'"${OUTPUT_JSON}"'"
  '

test -s "${OUTPUT_H5}"
test -s "${OUTPUT_JSON}"
grep -q 'frozen_encoder_latent_cache_implementation_smoke' "${OUTPUT_JSON}"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
sha256sum "${OUTPUT_H5}" "${OUTPUT_JSON}" "${OUTPUT_DIR}/provenance.txt" > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
