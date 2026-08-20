#!/usr/bin/env bash

# Remove one-time local build caches after Prometheus job 294570 completed and
# its outputs were copied into the SSD backup. Keep the validated SIF as the
# single offline container backup.

set -euo pipefail

ROOT="/home/chris/thesis"
EXPECTED_ROOT="/home/chris/thesis"
SIF="${ROOT}/tmp/container-build/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
# SIF serialization contains build metadata, so this independently built local
# backup does not byte-match the Prometheus SIF even though it uses the same
# pinned OCI image and exposes the same Python/PyTorch/CUDA runtime.
EXPECTED_SIF_SHA256="cccc563637d52857e8fc32721d3f36a3e26e3b0d1f9fc9a3ae9fffb9219251a0"

if [[ "$(realpath -e "${ROOT}")" != "${EXPECTED_ROOT}" ]]; then
  echo "Unexpected thesis root; refusing cleanup: ${ROOT}" >&2
  exit 2
fi
if [[ ! -f "${SIF}" ]]; then
  echo "Missing retained SIF backup: ${SIF}" >&2
  exit 2
fi
if [[ "$(sha256sum "${SIF}" | cut -d' ' -f1)" != "${EXPECTED_SIF_SHA256}" ]]; then
  echo "Retained SIF hash mismatch; refusing cleanup" >&2
  exit 3
fi

targets=(
  "${ROOT}/tmp/hi-lewm-env-test"
  "${ROOT}/tmp/hi-lewm-tools-test"
  "${ROOT}/tmp/pip-cache"
  "${ROOT}/tmp/conda-pkgs"
  "${ROOT}/tmp/container-build/pytorch-2.5.1-cu121.tar"
  "${ROOT}/tmp/container-build/singularity-cache"
  "${ROOT}/tmp/container-build/singularity-tmp"
)

expected_targets=(
  "${EXPECTED_ROOT}/tmp/hi-lewm-env-test"
  "${EXPECTED_ROOT}/tmp/hi-lewm-tools-test"
  "${EXPECTED_ROOT}/tmp/pip-cache"
  "${EXPECTED_ROOT}/tmp/conda-pkgs"
  "${EXPECTED_ROOT}/tmp/container-build/pytorch-2.5.1-cu121.tar"
  "${EXPECTED_ROOT}/tmp/container-build/singularity-cache"
  "${EXPECTED_ROOT}/tmp/container-build/singularity-tmp"
)

for index in "${!targets[@]}"; do
  if [[ -e "${targets[$index]}" ]]; then
    resolved="$(realpath -e -- "${targets[$index]}")"
    if [[ "${resolved}" != "${expected_targets[$index]}" ]]; then
      echo "Unexpected cleanup target: ${resolved}" >&2
      exit 4
    fi
  fi
done

rm -rf -- "${targets[@]}"

test -f "${SIF}"
test "$(sha256sum "${SIF}" | cut -d' ' -f1)" = "${EXPECTED_SIF_SHA256}"
echo "One-time local bootstrap caches removed; validated SIF backup retained."
