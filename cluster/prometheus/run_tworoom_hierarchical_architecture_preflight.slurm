#!/usr/bin/env bash

#SBATCH --job-name=tworoom-hi-arch
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-hi-arch-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-hi-arch-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/train_hierarchical_from_released_components.py"
RUNNER="${ROOT}/scripts/run_tworoom_hierarchical_architecture_preflight.slurm"
DATASET="${STABLEWM_HOME}/tworoom.h5"
BASE="${STABLEWM_HOME}/tworoom/lewm_object.ckpt"
OUTPUT_DIR="${STABLEWM_HOME}/repro/tworoom-hierarchical-architecture-preflight-job-${SLURM_JOB_ID}"
RECORD_DIR="${ROOT}/manifests/checkpoints/tworoom-hierarchical-architecture-preflight-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-hi-arch-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="bc5a128cea1e024d943c47be7b8b791d4afa7610700d81d7e49dc3ec77af2552"
EXPECTED_DATASET_BYTES=12775849984
EXPECTED_DATASET_SHA256="129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623"
EXPECTED_BASE_BYTES=72345376
EXPECTED_BASE_SHA256="83166a7ab38124d995f1206746990dce6ec627a31e469b8b5d8e0e5c980f0e86"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}" "${BASE}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom architecture input: ${required}" >&2; exit 2; fi
done
if [[ $(stat -c %s "${DATASET}") -ne ${EXPECTED_DATASET_BYTES} ]]; then echo "Dataset size mismatch" >&2; exit 2; fi
if [[ $(stat -c %s "${BASE}") -ne ${EXPECTED_BASE_BYTES} ]]; then echo "Base checkpoint size mismatch" >&2; exit 2; fi
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_DATASET_SHA256}  ${DATASET}" | sha256sum -c -
echo "${EXPECTED_BASE_SHA256}  ${BASE}" | sha256sum -c -
if [[ -e "${OUTPUT_DIR}" || -e "${RECORD_DIR}" ]]; then echo "Refusing to overwrite preflight" >&2; exit 2; fi
mkdir -p "${RECORD_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=outcome_blind_tworoom_hierarchical_architecture_preflight"
  echo "excluded_from_scientific_results=true"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}" "${BASE}" \
    "${CODE}/config/train/hi_lewm.yaml" \
    "${CODE}/config/train/data/hi_tworoom.yaml" \
    "${CODE}/h_le_wm/models/jepa.py" \
    "${CODE}/h_le_wm/models/latent_action.py" \
    "${CODE}/h_le_wm/train/pretrained.py" \
    "${CODE}/h_le_wm/train/steps.py" \
    "${CODE}/h_le_wm/train/waypoint_ops.py"
} > "${RECORD_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=3072
    export TMPDIR="'"${JOB_TMP}"'"
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" \
      --config-root "'"${CODE}"'/config/train" \
      --data-name hi_tworoom \
      --base-checkpoint "'"${BASE}"'" \
      --output-dir "'"${OUTPUT_DIR}"'" \
      --output-model-name tworoom_hierarchical_default \
      --seed 3072 --max-epochs 15 --batch-size 128 --num-workers 6 \
      --latent-action-dim 32 --architecture-only
  '

test -s "${OUTPUT_DIR}/effective-config.yaml"
test -s "${OUTPUT_DIR}/dataset-summary.json"
test -s "${OUTPUT_DIR}/architecture-summary.json"
cp -- "${OUTPUT_DIR}/dataset-summary.json" "${RECORD_DIR}/dataset-summary.json"
cp -- "${OUTPUT_DIR}/architecture-summary.json" "${RECORD_DIR}/architecture-summary.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${RECORD_DIR}/provenance.txt"
find "${RECORD_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${RECORD_DIR}/checksums.sha256"
sha256sum -c "${RECORD_DIR}/checksums.sha256"
