#!/usr/bin/env bash

# Prometheus compute nodes currently have no outbound internet route. The
# official storage guide permits direct dataset downloads to Lustre, so this
# lightweight I/O-only staging script is run on the login node. Extraction and
# expanded-file hashing remain SLURM work.

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
DOWNLOAD_DIR="${ROOT}/downloads/datasets"
ARTIFACT_DIR="${ROOT}/artifacts/hi-lewm"
LOCK_FILE="${ROOT}/tmp/stage-downloads.lock"
COMPLETE_FILE="${ROOT}/manifests/stage-downloads.complete"
PID_FILE="${ROOT}/manifests/stage-downloads.pid"

if [[ "${ROOT}" != "/lustreFS/data/superworld/ckontzias/thesis" ]]; then
  echo "Refusing to run with an unexpected project root: ${ROOT}" >&2
  exit 2
fi

mkdir -p "${DOWNLOAD_DIR}" "${ARTIFACT_DIR}" "${ROOT}/tmp" "${ROOT}/manifests"
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  echo "Another staging process already holds ${LOCK_FILE}" >&2
  exit 3
fi

printf '%s\n' "$$" > "${PID_FILE}"
trap 'rm -f -- "${PID_FILE}"' EXIT
rm -f -- "${COMPLETE_FILE}"

fetch_verified() {
  local label="$1"
  local url="$2"
  local destination="$3"
  local expected_sha="$4"

  if [[ -f "${destination}" ]] && \
     printf '%s  %s\n' "${expected_sha}" "${destination}" | sha256sum --check --status; then
    echo "[verified existing] ${label}: ${destination}"
    return 0
  fi

  local partial="${destination}.part"
  echo "[download start] ${label} -> ${partial}"
  curl --location --fail --silent --show-error \
    --retry 20 --retry-delay 10 --retry-connrefused \
    --speed-time 120 --speed-limit 1024 \
    --continue-at - --output "${partial}" "${url}"
  printf '%s  %s\n' "${expected_sha}" "${partial}" | sha256sum --check
  mv -- "${partial}" "${destination}"
  echo "[download verified] ${label}: ${destination}"
}

fetch_verified \
  "Hi-LeWM Zenodo artifact" \
  "https://zenodo.org/api/records/21353240/files/package.zip/content" \
  "${ARTIFACT_DIR}/package.zip" \
  "b89046841d679fe70f435540d62ae87b662ec34eb457919b098d152263f63967"

fetch_verified \
  "PushT dataset archive" \
  "https://huggingface.co/datasets/quentinll/lewm-pusht/resolve/655cd446b9929369d7d406001da85c15d1457850/pusht_expert_train.h5.zst?download=true" \
  "${DOWNLOAD_DIR}/pusht_expert_train.h5.zst" \
  "7cfbd6d90fa2f27876379a5ff169715a36ed82edbda64f9e5b5bfa34d212f318"

fetch_verified \
  "Cube dataset archive" \
  "https://huggingface.co/datasets/quentinll/lewm-cube/resolve/02a19a67a0dc8c9d6215f89c19e0a597691e152a/cube_single_expert.tar.zst?download=true" \
  "${DOWNLOAD_DIR}/cube_single_expert.tar.zst" \
  "3725d6a01abd492164441ef0a27e588f52b94a118fab56b96987b1a34a6c2600"

date --iso-8601=seconds > "${COMPLETE_FILE}"
echo "All source archives are present and verified."
