#!/usr/bin/env bash
#SBATCH --job-name=thesis-data
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/download-data-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/download-data-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
DATA_DIR="${ROOT}/data/stablewm"
DOWNLOAD_DIR="${ROOT}/downloads/datasets"
WORK_DIR="${ROOT}/tmp/dataset-download-${SLURM_JOB_ID}"

if [[ "${ROOT}" != "/lustreFS/data/superworld/ckontzias/thesis" ]]; then
  echo "Refusing to run with an unexpected project root: ${ROOT}" >&2
  exit 2
fi

mkdir -p "${DATA_DIR}" "${DOWNLOAD_DIR}" "${WORK_DIR}" "${ROOT}/logs"

ZSTD_BIN="$(command -v zstd || true)"
if [[ -z "${ZSTD_BIN}" && -x "${ROOT}/tools/zstd" ]]; then
  ZSTD_BIN="${ROOT}/tools/zstd"
fi
if [[ -z "${ZSTD_BIN}" ]]; then
  echo "zstd was not found in PATH or at ${ROOT}/tools/zstd" >&2
  exit 4
fi

ARTIFACT_URL="https://zenodo.org/api/records/21353240/files/package.zip/content"
ARTIFACT_OUTPUT="${ROOT}/artifacts/hi-lewm/package.zip"
ARTIFACT_SHA="b89046841d679fe70f435540d62ae87b662ec34eb457919b098d152263f63967"

PUSHT_REV="655cd446b9929369d7d406001da85c15d1457850"
PUSHT_ARCHIVE="${DOWNLOAD_DIR}/pusht_expert_train.h5.zst"
PUSHT_ARCHIVE_SHA="7cfbd6d90fa2f27876379a5ff169715a36ed82edbda64f9e5b5bfa34d212f318"
PUSHT_OUTPUT="${DATA_DIR}/pusht_expert_train.h5"
PUSHT_OUTPUT_SHA="b6ebd9ac94bbe9e383f6e7a9cd92d74e9aa665ea57b758ed3717b0ee7df8d4fb"
PUSHT_URL="https://huggingface.co/datasets/quentinll/lewm-pusht/resolve/${PUSHT_REV}/pusht_expert_train.h5.zst?download=true"

CUBE_REV="02a19a67a0dc8c9d6215f89c19e0a597691e152a"
CUBE_ARCHIVE="${DOWNLOAD_DIR}/cube_single_expert.tar.zst"
CUBE_ARCHIVE_SHA="3725d6a01abd492164441ef0a27e588f52b94a118fab56b96987b1a34a6c2600"
CUBE_OUTPUT="${DATA_DIR}/cube_single_expert.h5"
CUBE_OUTPUT_SHA="0664d507c4ff12009010644c9ae950836f954e700c172ccf22e7423af1a55625"
CUBE_URL="https://huggingface.co/datasets/quentinll/lewm-cube/resolve/${CUBE_REV}/cube_single_expert.tar.zst?download=true"

verify_file() {
  local expected_sha="$1"
  local path="$2"
  [[ -f "${path}" ]] && printf '%s  %s\n' "${expected_sha}" "${path}" | sha256sum --check --status
}

fetch_verified() {
  local url="$1"
  local destination="$2"
  local expected_sha="$3"

  if verify_file "${expected_sha}" "${destination}"; then
    echo "[verified existing archive] ${destination}"
    return 0
  fi

  local partial="${destination}.part"
  echo "[download] ${url}"
  curl --location --fail --retry 20 --retry-delay 10 --retry-connrefused \
    --continue-at - --output "${partial}" "${url}"
  printf '%s  %s\n' "${expected_sha}" "${partial}" | sha256sum --check
  mv -- "${partial}" "${destination}"
}

fetch_verified "${ARTIFACT_URL}" "${ARTIFACT_OUTPUT}" "${ARTIFACT_SHA}"

if verify_file "${PUSHT_OUTPUT_SHA}" "${PUSHT_OUTPUT}"; then
  echo "[verified existing dataset] ${PUSHT_OUTPUT}"
else
  fetch_verified "${PUSHT_URL}" "${PUSHT_ARCHIVE}" "${PUSHT_ARCHIVE_SHA}"
  pusht_tmp="${WORK_DIR}/pusht_expert_train.h5.tmp"
  rm -f -- "${pusht_tmp}"
  "${ZSTD_BIN}" --decompress --force -T0 "${PUSHT_ARCHIVE}" -o "${pusht_tmp}"
  printf '%s  %s\n' "${PUSHT_OUTPUT_SHA}" "${pusht_tmp}" | sha256sum --check
  mv -- "${pusht_tmp}" "${PUSHT_OUTPUT}"
  rm -f -- "${PUSHT_ARCHIVE}"
fi

if verify_file "${CUBE_OUTPUT_SHA}" "${CUBE_OUTPUT}"; then
  echo "[verified existing dataset] ${CUBE_OUTPUT}"
else
  fetch_verified "${CUBE_URL}" "${CUBE_ARCHIVE}" "${CUBE_ARCHIVE_SHA}"
  cube_extract_dir="${WORK_DIR}/cube-extract"
  rm -rf -- "${cube_extract_dir}"
  mkdir -p "${cube_extract_dir}"
  "${ZSTD_BIN}" --decompress --stdout -T0 "${CUBE_ARCHIVE}" | tar -xf - -C "${cube_extract_dir}"
  mapfile -t cube_matches < <(find "${cube_extract_dir}" -type f -name 'cube_single_expert.h5' -print)
  if [[ ${#cube_matches[@]} -ne 1 ]]; then
    echo "Expected exactly one cube_single_expert.h5, found ${#cube_matches[@]}" >&2
    exit 3
  fi
  printf '%s  %s\n' "${CUBE_OUTPUT_SHA}" "${cube_matches[0]}" | sha256sum --check
  mv -- "${cube_matches[0]}" "${CUBE_OUTPUT}"
  rm -rf -- "${cube_extract_dir}"
  rm -f -- "${CUBE_ARCHIVE}"
fi

printf '%s  %s\n' "${PUSHT_OUTPUT_SHA}" "${PUSHT_OUTPUT}" | sha256sum --check
printf '%s  %s\n' "${CUBE_OUTPUT_SHA}" "${CUBE_OUTPUT}" | sha256sum --check

rmdir "${WORK_DIR}" 2>/dev/null || true
echo "Both benchmark datasets are present and verified."
