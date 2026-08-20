#!/usr/bin/env bash

# Build the API-compatible environment required by the released Hi-LeWM
# evaluator. Run on the Prometheus login node after the base environment and
# CUDA container have been installed.

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
PINS="${ROOT}/tools/requirements-hi-lewm-artifact-cu121.in"
RESOLVED="${ROOT}/tools/requirements-hi-lewm-artifact-py311-cu121-resolved.txt"
FREEZE="${ROOT}/manifests/requirements-hi-lewm-artifact-py311-cu121-freeze.txt"
LOCK="${ROOT}/tmp/setup-hi-lewm-artifact-env.lock"

if [[ "${ROOT}" != "/lustreFS/data/superworld/ckontzias/thesis" ]]; then
  echo "Unexpected project root: ${ROOT}" >&2
  exit 2
fi
for required in "${IMAGE}" "${PINS}" "${RESOLVED}"; do
  if [[ ! -f "${required}" ]]; then
    echo "Missing required file: ${required}" >&2
    exit 2
  fi
done

mkdir -p "${ROOT}/envs" "${ROOT}/tmp" "${ROOT}/tmp/pip-cache" "${ROOT}/manifests"
exec 9>"${LOCK}"
flock -n 9 || { echo "Artifact environment build already running" >&2; exit 3; }

export APPTAINER_TMPDIR="${ROOT}/tmp/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
export PIP_CACHE_DIR="${ROOT}/tmp/pip-cache"
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONNOUSERSITE=1

if [[ -f "${ENV_DIR}/.hi-lewm-artifact-environment-complete" ]]; then
  echo "Artifact environment is already complete: ${ENV_DIR}"
else
  if [[ -e "${ENV_DIR}" ]]; then
    ENV_REAL="$(realpath -m -- "${ENV_DIR}")"
    if [[ "${ENV_REAL}" != "${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006" ]]; then
      echo "Refusing to clean unexpected environment path: ${ENV_REAL}" >&2
      exit 4
    fi
    rm -rf -- "${ENV_REAL}"
  fi

  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    /opt/conda/bin/python -m venv --system-site-packages "${ENV_DIR}"

  apptainer exec --cleanenv \
    --env PIP_CACHE_DIR="${PIP_CACHE_DIR}" \
    --env PIP_DISABLE_PIP_VERSION_CHECK=1 \
    --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    "${ENV_DIR}/bin/python" -m pip install \
      --constraint "${RESOLVED}" \
      --requirement "${PINS}"

  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    "${ENV_DIR}/bin/python" -m pip check

  touch "${ENV_DIR}/.hi-lewm-artifact-environment-complete"
fi

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" \
  "${ENV_DIR}/bin/python" -m pip list --local --format=freeze > "${FREEZE}"

diff -u "${RESOLVED}" "${FREEZE}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" \
  "${ENV_DIR}/bin/python" - <<'PY' \
  | tee "${ROOT}/manifests/hi-lewm-artifact-environment-runtime.txt"
import importlib.metadata as metadata
import platform
import torch
import torchvision
import stable_worldmodel as swm

print(f"python={platform.python_version()}")
print(f"torch={torch.__version__}")
print(f"torchvision={torchvision.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"cudnn={torch.backends.cudnn.version()}")
for package in ("stable-worldmodel", "stable-pretraining", "transformers"):
    print(f"{package}={metadata.version(package)}")
assert metadata.version("stable-worldmodel") == "0.0.6"
assert hasattr(swm.World, "evaluate_from_dataset")
print("world_evaluate_from_dataset=true")
PY

sha256sum \
  "${PINS}" \
  "${RESOLVED}" \
  "${FREEZE}" \
  > "${ROOT}/manifests/hi-lewm-artifact-environment-files.sha256"

echo "Hi-LeWM artifact-compatible environment build complete."
