#!/usr/bin/env bash

set -euo pipefail

if (( $# != 2 )); then
  echo "usage: $0 SOURCE_THESIS_DIR SNAPSHOT_DIR" >&2
  exit 2
fi

SOURCE_THESIS_DIR="$1"
SNAPSHOT_DIR="$2"

if [[ ! -d "${SOURCE_THESIS_DIR}/cluster/prometheus" ]]; then
  echo "Missing source cluster/prometheus directory: ${SOURCE_THESIS_DIR}" >&2
  exit 2
fi
if [[ ! -s "${SOURCE_THESIS_DIR}/thesis-master-protocol-and-paper-map-2026-07-28.md" ]]; then
  echo "Missing source master protocol: ${SOURCE_THESIS_DIR}" >&2
  exit 2
fi
if [[ -e "${SNAPSHOT_DIR}" ]]; then
  echo "Refusing to overwrite backup snapshot: ${SNAPSHOT_DIR}" >&2
  exit 2
fi

mkdir -p "${SNAPSHOT_DIR}"
cp -a "${SOURCE_THESIS_DIR}/cluster/prometheus" "${SNAPSHOT_DIR}/"
cp -a \
  "${SOURCE_THESIS_DIR}/thesis-master-protocol-and-paper-map-2026-07-28.md" \
  "${SNAPSHOT_DIR}/"

cd "${SNAPSHOT_DIR}"
find . -type f ! -name snapshot-checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > snapshot-checksums.sha256
chmod -R a-w "${SNAPSHOT_DIR}"

du -sh "${SNAPSHOT_DIR}"
find "${SNAPSHOT_DIR}" -type f | wc -l
