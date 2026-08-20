#!/usr/bin/env bash

#SBATCH --job-name=stage-reacher-acid-alt
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/stage-reacher-acid-alt-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/stage-reacher-acid-alt-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
DOWNLOAD_DIR="${ROOT}/downloads/lewm-reacher"
ARCHIVE="${DOWNLOAD_DIR}/reacher.tar.zst"
ARCHIVE_PARTIAL="${ARCHIVE}.partial"
DATASET="${STABLEWM_HOME}/reacher.h5"
DATASET_PARTIAL="${DATASET}.partial-${SLURM_JOB_ID}"
MODEL_DIR="${DOWNLOAD_DIR}/model"
MODEL_OBJECT="${STABLEWM_HOME}/reacher/lewm_object.ckpt"
DATASET_REVISION="e70a080d0d04c6072123c9ebd343acf7fff28dbf"
MODEL_REVISION="62adae4b71dc474ddf8f794c476ebfe737a743ca"
ARCHIVE_SHA256="4ff2385e49712caa89f21b8e0a246e2614b621d3f22cf2d1224d845e879a1cc2"
WEIGHTS_SHA256="eb70b1fd5409f8f81875d62f5ee5a20dd220a3128a477de66b5760f475f0f469"
JOB_TMP="/tmp/ckontzias-stage-reacher-${SLURM_JOB_ID}"

mkdir -p "${DOWNLOAD_DIR}" "${MODEL_DIR}" "${JOB_TMP}/extract" "${JOB_TMP}/apptainer"
cleanup() {
  rm -rf -- "${JOB_TMP}"
  rm -f -- "${DATASET_PARTIAL}"
}
trap cleanup EXIT

echo "job_id=${SLURM_JOB_ID}"
echo "node=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ ! -f "${ARCHIVE}" ]]; then
  if [[ ! -s "${ARCHIVE_PARTIAL}" || ! -s "${DOWNLOAD_DIR}/archive-download-complete.txt" ]]; then
    echo "Reacher archive has not completed login-host staging" >&2
    exit 3
  fi
  printf '%s  %s\n' "${ARCHIVE_SHA256}" "${ARCHIVE_PARTIAL}" | sha256sum --check --strict
  mv -- "${ARCHIVE_PARTIAL}" "${ARCHIVE}"
fi
printf '%s  %s\n' "${ARCHIVE_SHA256}" "${ARCHIVE}" | sha256sum --check --strict

if [[ ! -f "${DATASET}" ]]; then
  apptainer exec --cleanenv \
    --bind "${ROOT}:${ROOT}" \
    --bind "${JOB_TMP}:${JOB_TMP}" \
    "${IMAGE}" env \
    PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONNOUSERSITE=1 "${ENV_DIR}/bin/python" - \
    "${ARCHIVE}" "${DATASET_PARTIAL}" <<'PYTHON'
import pathlib
import shutil
import sys
import tarfile

import zstandard


archive, output = map(pathlib.Path, sys.argv[1:])
found = None
with archive.open("rb") as compressed:
    with zstandard.ZstdDecompressor().stream_reader(compressed) as stream:
        with tarfile.open(fileobj=stream, mode="r|") as bundle:
            for member in bundle:
                path = pathlib.PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise SystemExit(f"unsafe archive member: {member.name!r}")
                if not member.isfile() or path.suffix != ".h5":
                    continue
                if found is not None:
                    raise SystemExit(
                        f"expected one HDF5 member, found {found!r} and {member.name!r}"
                    )
                source = bundle.extractfile(member)
                if source is None:
                    raise SystemExit(f"could not read archive member: {member.name!r}")
                with output.open("wb") as destination:
                    shutil.copyfileobj(source, destination, length=8 * 1024 * 1024)
                found = member.name
if found is None:
    raise SystemExit("archive contains no HDF5 member")
PYTHON
  test -s "${DATASET_PARTIAL}"
  mv -- "${DATASET_PARTIAL}" "${DATASET}"
fi

test -s "${MODEL_DIR}/weights.pt"
printf '%s  %s\n' "${WEIGHTS_SHA256}" "${MODEL_DIR}/weights.pt" | sha256sum --check --strict

test -s "${MODEL_DIR}/config.json"

if [[ ! -f "${MODEL_OBJECT}" ]]; then
  export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
  export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
  apptainer exec --cleanenv \
    --bind "${ROOT}:${ROOT}" \
    --bind "${JOB_TMP}:${JOB_TMP}" \
    "${IMAGE}" /bin/bash -c '
      set -euo pipefail
      export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
      export PYTHONNOUSERSITE=1
      export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
      export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
      python "'"${CODE}"'/scripts/tools/convert_hf_weights_to_object_ckpt.py" \
        --weights "'"${MODEL_DIR}"'/weights.pt" \
        --config "'"${MODEL_DIR}"'/config.json" \
        --run-name reacher/lewm \
        --cache-dir "'"${STABLEWM_HOME}"'"
    '
fi

test -s "${DATASET}"
test -s "${MODEL_OBJECT}"
sha256sum "${ARCHIVE}" "${DATASET}" "${MODEL_DIR}/config.json" "${MODEL_DIR}/weights.pt" "${MODEL_OBJECT}" \
  > "${DOWNLOAD_DIR}/stage-checksums-job-${SLURM_JOB_ID}.sha256"
printf '%s\n' "dataset_revision=${DATASET_REVISION}" "model_revision=${MODEL_REVISION}" \
  "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "${DOWNLOAD_DIR}/stage-provenance-job-${SLURM_JOB_ID}.txt"
cat "${DOWNLOAD_DIR}/stage-checksums-job-${SLURM_JOB_ID}.sha256"
