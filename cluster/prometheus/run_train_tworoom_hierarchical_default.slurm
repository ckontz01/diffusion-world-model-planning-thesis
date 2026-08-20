#!/usr/bin/env bash

#SBATCH --job-name=tworoom-hi-train
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=long-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=36:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-hi-train-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-hi-train-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/train_hierarchical_from_released_components.py"
RUNNER="${ROOT}/scripts/run_train_tworoom_hierarchical_default.slurm"
DATASET="${STABLEWM_HOME}/tworoom.h5"
BASE="${STABLEWM_HOME}/tworoom/lewm_object.ckpt"
OUTPUT_DIR="${STABLEWM_HOME}/runs/tworoom_hierarchical_default-train-job-${SLURM_JOB_ID}"
CANONICAL_DIR="${STABLEWM_HOME}/runs/tworoom_hierarchical_default"
RECORD_DIR="${ROOT}/manifests/checkpoints/tworoom-hierarchical-train-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-hi-train-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="08449300c53eddc8d3ed498c3300a4f23db3ecef7065d6abd54ad9f9d3fe8d76"
EXPECTED_DATASET_BYTES=12775849984
EXPECTED_DATASET_SHA256="129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623"
EXPECTED_BASE_BYTES=72345376
EXPECTED_BASE_SHA256="83166a7ab38124d995f1206746990dce6ec627a31e469b8b5d8e0e5c980f0e86"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}" "${BASE}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom training input: ${required}" >&2; exit 2; fi
done
if [[ $(stat -c %s "${DATASET}") -ne ${EXPECTED_DATASET_BYTES} ]]; then echo "Dataset size mismatch" >&2; exit 2; fi
if [[ $(stat -c %s "${BASE}") -ne ${EXPECTED_BASE_BYTES} ]]; then echo "Base checkpoint size mismatch" >&2; exit 2; fi
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_DATASET_SHA256}  ${DATASET}" | sha256sum -c -
echo "${EXPECTED_BASE_SHA256}  ${BASE}" | sha256sum -c -
if [[ -e "${OUTPUT_DIR}" || -e "${RECORD_DIR}" || -e "${CANONICAL_DIR}" ]]; then
  echo "Refusing to overwrite a TwoRoom production checkpoint path" >&2
  exit 2
fi
mkdir -p "${RECORD_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_independently_trained_hierarchical_checkpoint"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "seed=3072"
  echo "epochs=15"
  echo "batch_size=128"
  echo "latent_action_dim=32"
  echo "low_level_frozen=true"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}" "${BASE}" \
    "${CODE}/config/train/hi_lewm.yaml" \
    "${CODE}/config/train/data/hi_tworoom.yaml" \
    "${CODE}/h_le_wm/models/jepa.py" \
    "${CODE}/h_le_wm/models/latent_action.py" \
    "${CODE}/h_le_wm/train/pretrained.py" \
    "${CODE}/h_le_wm/train/steps.py" \
    "${CODE}/h_le_wm/train/waypoint_ops.py"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${RECORD_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
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
      --latent-action-dim 32
  '

FINAL="${OUTPUT_DIR}/tworoom_hierarchical_default_epoch_15_object.ckpt"
test -s "${FINAL}"
test -s "${OUTPUT_DIR}/COMPLETE.json"
ln -s -- "${OUTPUT_DIR}" "${CANONICAL_DIR}"
sha256sum "${FINAL}" > "${RECORD_DIR}/final-checkpoint.sha256"
cp -- "${OUTPUT_DIR}/COMPLETE.json" "${OUTPUT_DIR}/effective-config.yaml" \
  "${OUTPUT_DIR}/dataset-summary.json" "${OUTPUT_DIR}/architecture-summary.json" \
  "${OUTPUT_DIR}/compatibility-summary.json" \
  "${RECORD_DIR}/"
echo "canonical_symlink=${CANONICAL_DIR}" >> "${RECORD_DIR}/provenance.txt"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${RECORD_DIR}/provenance.txt"
find "${RECORD_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${RECORD_DIR}/checksums.sha256"
sha256sum -c "${RECORD_DIR}/checksums.sha256"
