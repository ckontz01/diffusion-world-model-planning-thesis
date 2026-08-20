#!/usr/bin/env bash

# Run on the Prometheus login node after pull_pytorch_container.sh.
# Downloads happen here because compute nodes do not have outbound internet.

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-py311-cu121"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
PINS="${ROOT}/tools/requirements-prometheus-cu121.in"
RESOLVED="${ROOT}/tools/requirements-prometheus-py311-cu121-resolved.txt"
LOCK="${ROOT}/tmp/setup-hi-lewm-env.lock"

if [[ "${ROOT}" != "/lustreFS/data/superworld/ckontzias/thesis" ]]; then
  echo "Unexpected project root: ${ROOT}" >&2
  exit 2
fi
if [[ ! -f "${IMAGE}" ]]; then
  echo "Missing container: ${IMAGE}" >&2
  exit 2
fi
if [[ ! -f "${PINS}" ]]; then
  echo "Missing requirements input: ${PINS}" >&2
  exit 2
fi
if [[ ! -f "${RESOLVED}" ]]; then
  echo "Missing resolved requirements: ${RESOLVED}" >&2
  exit 2
fi

mkdir -p \
  "${ROOT}/envs" \
  "${ROOT}/tmp" \
  "${ROOT}/tmp/conda-pkgs" \
  "${ROOT}/tmp/pip-cache" \
  "${ROOT}/manifests"
exec 9>"${LOCK}"
flock -n 9 || { echo "Environment build already running" >&2; exit 3; }

export APPTAINER_TMPDIR="${ROOT}/tmp/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
export PYTHONNOUSERSITE=1
export CONDA_PKGS_DIRS="${ROOT}/tmp/conda-pkgs"
export PIP_CACHE_DIR="${ROOT}/tmp/pip-cache"
export PIP_DISABLE_PIP_VERSION_CHECK=1

if [[ -f "${ENV_DIR}/.hi-lewm-environment-complete" ]]; then
  echo "Environment is already complete: ${ENV_DIR}"
else
  if [[ -e "${ENV_DIR}" ]]; then
    ENV_REAL="$(realpath -m -- "${ENV_DIR}")"
    EXPECTED_ENV="${ROOT}/envs/hi-lewm-py311-cu121"
    if [[ "${ENV_REAL}" != "${EXPECTED_ENV}" ]]; then
      echo "Refusing to clean unexpected environment path: ${ENV_REAL}" >&2
      exit 4
    fi
    rm -rf -- "${ENV_REAL}"
  fi

  # Reuse the immutable image's matched Python/PyTorch/CUDA stack. This avoids
  # a second copy of all CUDA libraries and makes the exact SIF digest the
  # source of truth for the GPU runtime.
  apptainer exec --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    /opt/conda/bin/python -m venv --system-site-packages "${ENV_DIR}"

  apptainer exec --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    "${ENV_DIR}/bin/python" -m pip install \
      --constraint "${RESOLVED}" \
      --requirement "${PINS}"

  apptainer exec --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    "${ENV_DIR}/bin/python" -m pip check

  touch "${ENV_DIR}/.hi-lewm-environment-complete"
fi

# The runtime image intentionally omits development tools, but the artifact's
# baseline-integrity validator invokes the git CLI. Keep that small toolchain in
# its own recorded Conda prefix instead of modifying the immutable SIF.
if [[ ! -x "${TOOLS_DIR}/bin/git" ]]; then
  if [[ -e "${TOOLS_DIR}" ]]; then
    TOOLS_REAL="$(realpath -m -- "${TOOLS_DIR}")"
    EXPECTED_TOOLS="${ROOT}/envs/hi-lewm-tools"
    if [[ "${TOOLS_REAL}" != "${EXPECTED_TOOLS}" ]]; then
      echo "Refusing to clean unexpected tools path: ${TOOLS_REAL}" >&2
      exit 4
    fi
    rm -rf -- "${TOOLS_REAL}"
  fi
  apptainer exec --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    /opt/conda/bin/conda create --yes --prefix "${TOOLS_DIR}" \
      --channel conda-forge git
fi

apptainer exec --bind "${ROOT}:${ROOT}" "${IMAGE}" \
  "${ENV_DIR}/bin/python" -m pip list --local --format=freeze \
  > "${ROOT}/manifests/requirements-prometheus-py311-cu121-freeze.txt"

apptainer exec --bind "${ROOT}:${ROOT}" "${IMAGE}" \
  "${ENV_DIR}/bin/python" - <<'PY' \
  | tee "${ROOT}/manifests/hi-lewm-environment-runtime.txt"
import importlib.metadata as metadata
import platform
import torch
import torchvision

print(f"python={platform.python_version()}")
print(f"torch={torch.__version__}")
print(f"torchvision={torchvision.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"cudnn={torch.backends.cudnn.version()}")
for package in ("stable-worldmodel", "stable-pretraining", "transformers"):
    print(f"{package}={metadata.version(package)}")
PY

apptainer exec --bind "${ROOT}:${ROOT}" "${IMAGE}" \
  "${TOOLS_DIR}/bin/git" --version \
  | tee "${ROOT}/manifests/hi-lewm-git-runtime.txt"
apptainer exec --bind "${ROOT}:${ROOT}" "${IMAGE}" \
  /opt/conda/bin/conda list --prefix "${TOOLS_DIR}" --explicit \
  > "${ROOT}/manifests/hi-lewm-tools-conda-explicit.txt"

sha256sum \
  "${PINS}" \
  "${RESOLVED}" \
  "${ROOT}/manifests/requirements-prometheus-py311-cu121-freeze.txt" \
  "${ROOT}/manifests/hi-lewm-tools-conda-explicit.txt" \
  > "${ROOT}/manifests/hi-lewm-environment-files.sha256"

echo "Hi-LeWM environment build complete."
