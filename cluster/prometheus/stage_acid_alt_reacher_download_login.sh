#!/usr/bin/env bash
# Network-transfer-only Reacher staging. Run on the Prometheus login host.

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
DOWNLOAD_DIR="${ROOT}/downloads/lewm-reacher"
ARCHIVE_PARTIAL="${DOWNLOAD_DIR}/reacher.tar.zst.partial"
MODEL_DIR="${DOWNLOAD_DIR}/model"
DATASET_REVISION="e70a080d0d04c6072123c9ebd343acf7fff28dbf"
MODEL_REVISION="62adae4b71dc474ddf8f794c476ebfe737a743ca"
WEIGHTS_SHA256="eb70b1fd5409f8f81875d62f5ee5a20dd220a3128a477de66b5760f475f0f469"
LOCK_DIR="${DOWNLOAD_DIR}/.login-download.lock"

mkdir -p "${DOWNLOAD_DIR}" "${MODEL_DIR}"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "Another Reacher login download appears to be active: ${LOCK_DIR}" >&2
  exit 2
fi
cleanup() {
  rmdir -- "${LOCK_DIR}" 2>/dev/null || true
}
trap cleanup EXIT

echo "host=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ ! -f "${DOWNLOAD_DIR}/reacher.tar.zst" ]]; then
  curl --fail --location --silent --show-error \
    --retry 20 --retry-delay 15 --continue-at - \
    --output "${ARCHIVE_PARTIAL}" \
    "https://huggingface.co/datasets/quentinll/lewm-reacher/resolve/${DATASET_REVISION}/reacher.tar.zst?download=true"
  printf '%s\n' \
    "archive_partial=${ARCHIVE_PARTIAL}" \
    "archive_bytes=$(stat -c %s "${ARCHIVE_PARTIAL}")" \
    "download_finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "${DOWNLOAD_DIR}/archive-download-complete.txt"
fi

for filename in config.json weights.pt; do
  if [[ ! -f "${MODEL_DIR}/${filename}" ]]; then
    curl --fail --location --silent --show-error \
      --retry 20 --retry-delay 15 --continue-at - \
      --output "${MODEL_DIR}/${filename}.partial" \
      "https://huggingface.co/quentinll/lewm-reacher/resolve/${MODEL_REVISION}/${filename}?download=true"
    mv -- "${MODEL_DIR}/${filename}.partial" "${MODEL_DIR}/${filename}"
  fi
done
printf '%s  %s\n' "${WEIGHTS_SHA256}" "${MODEL_DIR}/weights.pt" \
  | sha256sum --check --strict
sha256sum "${MODEL_DIR}/config.json" "${MODEL_DIR}/weights.pt" \
  > "${MODEL_DIR}/sha256.txt"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
