#!/usr/bin/env bash

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
REVISION="77adaae0bc31deab21c93740d1f8bb947cd0bdec"
SOURCE_DIR="${ROOT}/data/stablewm/sources/quentinll-lewm-tworooms-model-${REVISION}"
WEIGHTS="${SOURCE_DIR}/weights.pt"
CONFIG="${SOURCE_DIR}/config.json"
EXPECTED_WEIGHTS_BYTES=72290849
EXPECTED_WEIGHTS_SHA256="566f223624ea4bfb39dbfe6ae731198dd6ea73b7b8919fed6b1ecafca810f7dd"
WEIGHTS_URL="https://huggingface.co/quentinll/lewm-tworooms/resolve/${REVISION}/weights.pt?download=true"
CONFIG_URL="https://huggingface.co/quentinll/lewm-tworooms/resolve/${REVISION}/config.json?download=true"

mkdir -p "${SOURCE_DIR}"

download_once() {
  local url="$1"
  local destination="$2"
  local partial="${destination}.partial"
  if [[ -e "${destination}" ]]; then
    return 0
  fi
  rm -f -- "${partial}"
  curl --fail --location --retry 5 --retry-delay 3 \
    --output "${partial}" "${url}"
  test -s "${partial}"
  mv -- "${partial}" "${destination}"
}

download_once "${WEIGHTS_URL}" "${WEIGHTS}"
download_once "${CONFIG_URL}" "${CONFIG}"

if [[ $(stat -c %s "${WEIGHTS}") -ne ${EXPECTED_WEIGHTS_BYTES} ]]; then
  echo "TwoRoom weights have the wrong byte size" >&2
  exit 2
fi
echo "${EXPECTED_WEIGHTS_SHA256}  ${WEIGHTS}" | sha256sum -c -
python3 -m json.tool "${CONFIG}" >/dev/null

{
  echo "source_model=https://huggingface.co/quentinll/lewm-tworooms"
  echo "source_revision=${REVISION}"
  echo "weights_url=${WEIGHTS_URL}"
  echo "config_url=${CONFIG_URL}"
  echo "weights_bytes=$(stat -c %s "${WEIGHTS}")"
  echo "config_bytes=$(stat -c %s "${CONFIG}")"
  sha256sum "${WEIGHTS}" "${CONFIG}"
} > "${SOURCE_DIR}/source-manifest.txt"

sha256sum "${SOURCE_DIR}/source-manifest.txt"
cat "${SOURCE_DIR}/source-manifest.txt"
