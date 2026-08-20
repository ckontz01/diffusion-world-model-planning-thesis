#!/usr/bin/env bash

# Run on the Prometheus login node, which has outbound internet access.

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
OCI_DIGEST="sha256:831247999fbf7e08f61b3e39f6d77ee434f38f6f07f769d00db451e853878067"
SOURCE="docker://pytorch/pytorch@${OCI_DIGEST}"
LOCK="${ROOT}/tmp/pull-pytorch-2.5.1.lock"

if [[ "${ROOT}" != "/lustreFS/data/superworld/ckontzias/thesis" ]]; then
  echo "Unexpected project root: ${ROOT}" >&2
  exit 2
fi

mkdir -p "${ROOT}/containers" "${ROOT}/tmp/apptainer" "${ROOT}/tmp/apptainer-cache" "${ROOT}/manifests"
exec 9>"${LOCK}"
flock -n 9 || { echo "Container pull already running" >&2; exit 3; }

export APPTAINER_TMPDIR="${ROOT}/tmp/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"

if [[ ! -f "${IMAGE}" ]]; then
  apptainer pull --disable-cache "${IMAGE}.part" "${SOURCE}"
  mv -- "${IMAGE}.part" "${IMAGE}"
fi

sha256sum "${IMAGE}" | tee "${ROOT}/manifests/pytorch-container.sha256"
{
  echo "source=${SOURCE}"
  echo "oci_digest=${OCI_DIGEST}"
  echo "sif_path=${IMAGE}"
  echo "recorded_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "${ROOT}/manifests/pytorch-container-source.txt"
apptainer inspect --json "${IMAGE}" > "${ROOT}/manifests/pytorch-container-inspect.json"
apptainer exec "${IMAGE}" python - <<'PY' | tee "${ROOT}/manifests/pytorch-container-runtime.txt"
import platform
import torch
import torchvision
print(f"python={platform.python_version()}")
print(f"torch={torch.__version__}")
print(f"torchvision={torchvision.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"cudnn={torch.backends.cudnn.version()}")
PY

echo "Container pull and inspection complete."
