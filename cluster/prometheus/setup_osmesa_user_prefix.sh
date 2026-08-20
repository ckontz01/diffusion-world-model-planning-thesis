#!/usr/bin/env bash

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
OUTPUT="${ROOT}/software/osmesa-ubuntu22.04"
APT_STATE="${OUTPUT}/apt-state"
DOWNLOADS="${OUTPUT}/packages"
PREFIX="${OUTPUT}/prefix"
SOURCES="${ROOT}/scripts/ubuntu-jammy-https.sources.list"

if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing to overwrite OSMesa user prefix: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${APT_STATE}/lists/partial" "${APT_STATE}/cache/archives/partial" \
  "${DOWNLOADS}" "${PREFIX}"
test -s "${SOURCES}"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${APT_STATE}/lists:/var/lib/apt/lists" \
  --bind "${APT_STATE}/cache:/var/cache/apt" \
  "${IMAGE}" apt-get \
    -o "Dir::Etc::sourcelist=${SOURCES}" \
    -o "Dir::Etc::sourceparts=-" \
    -o Acquire::ForceIPv4=true update

for package in \
  libosmesa6 libglapi-mesa libllvm15 libdrm2 libedit2 libxml2 \
  libpciaccess0 libbsd0 libmd0 libicu70; do
  apptainer exec --cleanenv \
    --bind "${ROOT}:${ROOT}" \
    --bind "${APT_STATE}/lists:/var/lib/apt/lists" \
    --bind "${APT_STATE}/cache:/var/cache/apt" \
    --pwd "${DOWNLOADS}" \
    "${IMAGE}" apt-get \
      -o "Dir::Etc::sourcelist=${SOURCES}" \
      -o "Dir::Etc::sourceparts=-" \
      -o Acquire::ForceIPv4=true download "${package}"
done

shopt -s nullglob
packages=("${DOWNLOADS}"/*.deb)
if [[ ${#packages[@]} -ne 10 ]]; then
  echo "Expected exactly ten downloaded OSMesa packages; found ${#packages[@]}" >&2
  exit 2
fi
for package in "${packages[@]}"; do
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    dpkg-deb -x "${package}" "${PREFIX}"
done

LIBDIR="${PREFIX}/usr/lib/x86_64-linux-gnu"
test -s "${LIBDIR}/libOSMesa.so.8"
{
  echo "classification=user_prefix_osmesa_runtime"
  echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "base_image=${IMAGE}"
  sha256sum "${IMAGE}"
  for package in "${packages[@]}"; do
    apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" \
      dpkg-deb -f "${package}" Package Version Architecture
    sha256sum "${package}"
  done
  echo "ldd_libOSMesa_begin"
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" \
    env LD_LIBRARY_PATH="${LIBDIR}" ldd "${LIBDIR}/libOSMesa.so.8"
  echo "ldd_libOSMesa_end"
} > "${OUTPUT}/manifest.txt"
if grep -q 'not found' "${OUTPUT}/manifest.txt"; then
  echo "OSMesa user prefix still has an unresolved shared library" >&2
  exit 2
fi

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /bin/bash -c '
  set -euo pipefail
  export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  export PYTHONNOUSERSITE=1
  export LD_LIBRARY_PATH="'"${LIBDIR}"':${LD_LIBRARY_PATH:-}"
  export MUJOCO_GL=osmesa
  export PYOPENGL_PLATFORM=osmesa
  python -c "from dm_control import mjcf; print(\"osmesa_dm_control_import=ok\")"
' | tee "${OUTPUT}/import-test.txt"

find "${PREFIX}" -type f -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT}/installed-files.sha256"
sha256sum "${OUTPUT}/manifest.txt" "${OUTPUT}/import-test.txt" \
  "${OUTPUT}/installed-files.sha256" > "${OUTPUT}/checksums.sha256"
sha256sum -c "${OUTPUT}/checksums.sha256"
