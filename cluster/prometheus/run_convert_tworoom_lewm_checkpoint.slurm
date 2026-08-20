#!/usr/bin/env bash

#SBATCH --job-name=tworoom-lewm-convert
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-lewm-convert-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-lewm-convert-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
REVISION="77adaae0bc31deab21c93740d1f8bb947cd0bdec"
SOURCE_DIR="${STABLEWM_HOME}/sources/quentinll-lewm-tworooms-model-${REVISION}"
WEIGHTS="${SOURCE_DIR}/weights.pt"
CONFIG="${SOURCE_DIR}/config.json"
CONVERTER="${CODE}/scripts/tools/convert_hf_weights_to_object_ckpt.py"
RUNNER="${ROOT}/scripts/run_convert_tworoom_lewm_checkpoint.slurm"
OUTPUT="${STABLEWM_HOME}/tworoom/lewm_object.ckpt"
OUTPUT_DIR="${ROOT}/manifests/checkpoints/tworoom-lewm-conversion-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-convert-${SLURM_JOB_ID}"

EXPECTED_WEIGHTS_BYTES=72290849
EXPECTED_WEIGHTS_SHA256="566f223624ea4bfb39dbfe6ae731198dd6ea73b7b8919fed6b1ecafca810f7dd"
EXPECTED_CONFIG_BYTES=1313
EXPECTED_CONFIG_SHA256="2564086e961e7b5c7c04dffc451091115b389a590645ff19653c64fd0bc16e09"
EXPECTED_CONVERTER_SHA256="4ec630ac7b22d7716c2692fc075975910a6496cb6029260a1eaa18bc5f0fb2d1"

for required in "${IMAGE}" "${WEIGHTS}" "${CONFIG}" "${CONVERTER}" "${RUNNER}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing TwoRoom conversion input: ${required}" >&2
    exit 2
  fi
done
if [[ $(stat -c %s "${WEIGHTS}") -ne ${EXPECTED_WEIGHTS_BYTES} ]]; then
  echo "TwoRoom weights byte-size mismatch" >&2
  exit 2
fi
if [[ $(stat -c %s "${CONFIG}") -ne ${EXPECTED_CONFIG_BYTES} ]]; then
  echo "TwoRoom config byte-size mismatch" >&2
  exit 2
fi
echo "${EXPECTED_WEIGHTS_SHA256}  ${WEIGHTS}" | sha256sum -c -
echo "${EXPECTED_CONFIG_SHA256}  ${CONFIG}" | sha256sum -c -
echo "${EXPECTED_CONVERTER_SHA256}  ${CONVERTER}" | sha256sum -c -
if [[ -e "${OUTPUT}" || -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite a TwoRoom checkpoint or conversion record" >&2
  exit 2
fi

mkdir -p "$(dirname "${OUTPUT}")" "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=tworoom_official_lewm_checkpoint_conversion"
  echo "job_id=${SLURM_JOB_ID}"
  echo "source_model=https://huggingface.co/quentinll/lewm-tworooms"
  echo "source_revision=${REVISION}"
  echo "strict_state_dict_load=true"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${WEIGHTS}" "${CONFIG}" "${CONVERTER}" "${RUNNER}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export TMPDIR="'"${JOB_TMP}"'"
    cd "'"${CODE}"'"
    python "'"${CONVERTER}"'" \
      --weights "'"${WEIGHTS}"'" \
      --config "'"${CONFIG}"'" \
      --run-name tworoom/lewm \
      --cache-dir "'"${STABLEWM_HOME}"'"
    python - "'"${OUTPUT}"'" <<"PY"
import sys
import torch

path = sys.argv[1]
model = torch.load(path, map_location="cpu", weights_only=False)
parameters = list(model.parameters())
assert parameters, "Converted model has no parameters"
assert all(not parameter.requires_grad for parameter in parameters)
print(f"converted_type={type(model).__module__}.{type(model).__name__}")
print(f"parameter_count={sum(parameter.numel() for parameter in parameters)}")
PY
  ' | tee "${OUTPUT_DIR}/conversion-and-load-test.txt"

test -s "${OUTPUT}"
sha256sum "${OUTPUT}" > "${OUTPUT_DIR}/checkpoint.sha256"
stat -c 'checkpoint_bytes=%s' "${OUTPUT}" > "${OUTPUT_DIR}/checkpoint-size.txt"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
