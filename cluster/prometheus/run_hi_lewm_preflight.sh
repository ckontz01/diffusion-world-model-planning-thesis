#!/usr/bin/env bash

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-py311-cu121"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
EXPECTED_LEWM_COMMIT="8edfeb336732b5f3ce7b8b210d0ba370a09e2cac"

for required in "${IMAGE}" "${ENV_DIR}/.hi-lewm-environment-complete" "${CODE}/scripts/run_pusht_smoke.sh"; do
  if [[ ! -e "${required}" ]]; then
    echo "Missing required path: ${required}" >&2
    exit 2
  fi
done

ACTUAL_LEWM_COMMIT="$(git -C "${CODE}/third_party/lewm" rev-parse HEAD)"
if [[ "${ACTUAL_LEWM_COMMIT}" != "${EXPECTED_LEWM_COMMIT}" ]]; then
  echo "LeWM commit mismatch: expected=${EXPECTED_LEWM_COMMIT} actual=${ACTUAL_LEWM_COMMIT}" >&2
  exit 3
fi
echo "[ok] third_party/lewm commit=${ACTUAL_LEWM_COMMIT}"

export APPTAINER_TMPDIR="${ROOT}/tmp/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /bin/bash -c '
  set -euo pipefail
  export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  export PYTHONNOUSERSITE=1
  export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
  export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
  export MPLBACKEND=Agg
  cd "'"${CODE}"'"
  python -m h_le_wm.validate preflight --tier supported-first-class
  bash scripts/run_pusht_smoke.sh --dry-run
'

echo "Hi-LeWM preflight and smoke dry-run passed."
