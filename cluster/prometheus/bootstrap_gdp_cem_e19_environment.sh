#!/usr/bin/env bash
set -euo pipefail

ROOT=/lustreFS/data/superworld/ckontzias/thesis
TOOLS=${ROOT}/tools/e19-miniforge-26.3.2-2
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
DOWNLOAD=${ROOT}/downloads/gdp-cem-e19/environment
INSTALLER=${DOWNLOAD}/Miniforge3-26.3.2-2-Linux-x86_64.sh
INSTALLER_URL=https://github.com/conda-forge/miniforge/releases/download/26.3.2-2/Miniforge3-26.3.2-2-Linux-x86_64.sh
INSTALLER_SHA256=42260ffe3830fb953d5eee1bbb32229ff06aa7c3833c1ed7a9a0420a95685d94
LOCK=${ENV_DIR}/E19-ENVIRONMENT-LOCK.txt

mkdir -p "${DOWNLOAD}" "${ROOT}/tools" "${ROOT}/envs"
if [[ ! -f "${INSTALLER}" ]]; then
  curl --fail --location --silent --show-error --retry 8 --retry-delay 10 \
    --output "${INSTALLER}.partial" "${INSTALLER_URL}"
  mv -- "${INSTALLER}.partial" "${INSTALLER}"
fi
printf '%s  %s\n' "${INSTALLER_SHA256}" "${INSTALLER}" | sha256sum --check --strict

if [[ ! -x "${TOOLS}/bin/mamba" ]]; then
  test ! -e "${TOOLS}"
  bash "${INSTALLER}" -b -p "${TOOLS}"
fi

if [[ -f "${LOCK}" ]]; then
  sha256sum --check "${ENV_DIR}/sha256.txt" >/dev/null
  grep -Fx 'Python 3.10.16' "${LOCK}" >/dev/null
  "${ENV_DIR}/bin/python" -c 'import torch; assert torch.__version__ == "2.5.1+cu121" and torch.version.cuda == "12.1"'
  printf 'environment=%s\nstatus=already-complete\n' "${ENV_DIR}"
  exit 0
fi

test ! -e "${ENV_DIR}"
"${TOOLS}/bin/mamba" create --yes --prefix "${ENV_DIR}" python=3.10.16 pip=25.1
"${ENV_DIR}/bin/python" -m pip install --no-cache-dir \
  --index-url https://download.pytorch.org/whl/cu121 \
  torch==2.5.1 torchvision==0.20.1
"${ENV_DIR}/bin/python" -m pip install --no-cache-dir \
  numpy==2.2.6 \
  stable-pretraining==0.1.7 \
  gymnasium==1.3.0 \
  ogbench==1.2.1 \
  lancedb==0.33.0 \
  pylance==7.0.0 \
  pyarrow==24.0.0 \
  h5py==3.16.0 \
  hdf5plugin==7.0.0 \
  einops==0.8.2 \
  transformers==5.1.0 \
  huggingface-hub==1.3.0 \
  opencv-python-headless==4.13.0.92 \
  pygame==2.6.1 \
  pymunk==6.8.0 \
  shapely==2.1.2 \
  pillow \
  tqdm \
  rich \
  loguru \
  tabulate \
  'pytest>=8,<9'

{
  "${ENV_DIR}/bin/python" --version
  "${ENV_DIR}/bin/python" -c 'import torch; print(f"torch={torch.__version__}"); print(f"torch_cuda={torch.version.cuda}")'
  printf '%s\n' \
    'source_environment=PKU-ML/SAGE@8219029fd52e89157e05aebb998ab26f0ef46966/environment.yml' \
    'transport_index=https://download.pytorch.org/whl/cu121' \
    'upstream_install_failure=transformers==5.1.2 has no published PyPI distribution' \
    'dependency_only_compatibility=transformers==5.1.0 (nearest published version in requested minor; unused lazy PreJEPA path)' \
    'dependency_resolution=huggingface-hub==1.3.0 (minimum satisfying transformers==5.1.0 and upstream huggingface-hub>=0.36)' \
    'explicit_runtime_addition=hdf5plugin==7.0.0 (required by bundled HDF5 reader; omitted from upstream environment.yml)' \
    "miniforge_installer_sha256=${INSTALLER_SHA256}"
} > "${LOCK}"
"${ENV_DIR}/bin/python" -m pip freeze --all > "${ENV_DIR}/pip-freeze.txt"
"${ENV_DIR}/bin/python" - <<'PY'
import h5py, hdf5plugin, lancedb, numpy, pyarrow, torch, torchvision
assert torch.__version__ == "2.5.1+cu121", torch.__version__
assert torch.version.cuda == "12.1", torch.version.cuda
assert numpy.__version__ == "2.2.6"
assert h5py.__version__ == "3.16.0"
assert pyarrow.__version__ == "24.0.0"
assert lancedb.__version__ == "0.33.0"
assert torchvision.__version__ == "0.20.1+cu121"
PY
sha256sum "${LOCK}" "${ENV_DIR}/pip-freeze.txt" > "${ENV_DIR}/sha256.txt"
chmod a-w "${LOCK}" "${ENV_DIR}/pip-freeze.txt" "${ENV_DIR}/sha256.txt"
printf 'environment=%s\nstatus=created\n' "${ENV_DIR}"
