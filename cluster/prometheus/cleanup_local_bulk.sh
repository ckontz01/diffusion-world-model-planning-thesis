#!/usr/bin/env bash

# One-time cleanup after Prometheus migration job 294548 verified the expanded
# datasets and the released checkpoints/artifact passed their manifests.

set -euo pipefail

ROOT="/home/chris/thesis"
EXPECTED_ROOT="/home/chris/thesis"

if [[ "$(realpath -e "${ROOT}")" != "${EXPECTED_ROOT}" ]]; then
  echo "Unexpected thesis root; refusing cleanup: ${ROOT}" >&2
  exit 2
fi

targets=(
  "${ROOT}/data"
  "${ROOT}/vendor/hi-lewm/downloads"
  "${ROOT}/vendor/hi-lewm/artifact/package/checkpoints"
  "${ROOT}/vendor/hi-lewm/artifact/__MACOSX"
)

expected_targets=(
  "${EXPECTED_ROOT}/data"
  "${EXPECTED_ROOT}/vendor/hi-lewm/downloads"
  "${EXPECTED_ROOT}/vendor/hi-lewm/artifact/package/checkpoints"
  "${EXPECTED_ROOT}/vendor/hi-lewm/artifact/__MACOSX"
)

for i in "${!targets[@]}"; do
  resolved="$(realpath -e "${targets[$i]}")"
  if [[ "${resolved}" != "${expected_targets[$i]}" ]]; then
    echo "Unexpected cleanup target: ${resolved}" >&2
    exit 3
  fi
done

data_file_count="$(find "${ROOT}/data" -xdev -type f | wc -l)"
if [[ "${data_file_count}" != "8" ]]; then
  echo "Expected exactly 8 verified files under ${ROOT}/data; found ${data_file_count}" >&2
  exit 4
fi

rm -rf -- "${targets[@]}"
echo "Verified reproducible bulk copies removed from ${ROOT}."
