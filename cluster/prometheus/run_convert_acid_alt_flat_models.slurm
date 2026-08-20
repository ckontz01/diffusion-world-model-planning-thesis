#!/usr/bin/env bash

#SBATCH --job-name=convert-flat-lewm
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/convert-flat-lewm-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/convert-flat-lewm-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SOURCE_ROOT="${ROOT}/downloads/acid-alternative/flat-lewm-models"
PUSHT_SOURCE="${SOURCE_ROOT}/pusht-22b330c28c27ead4bfd1888615af1340e3fe9052"
CUBE_SOURCE="${SOURCE_ROOT}/cube-b0747c5002e86d2ce8f3cd8178004b97524c587d"
PUSHT_OUTPUT="${STABLEWM_HOME}/pusht/lewm_hf_22b330c_object.ckpt"
CUBE_OUTPUT="${STABLEWM_HOME}/cube/lewm_hf_b0747c5_object.ckpt"
PROVENANCE="${SOURCE_ROOT}/conversion-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-convert-flat-lewm-${SLURM_JOB_ID}"

for required in \
  "${IMAGE}" \
  "${PUSHT_SOURCE}/weights.pt" \
  "${PUSHT_SOURCE}/config.json" \
  "${CUBE_SOURCE}/weights.pt" \
  "${CUBE_SOURCE}/config.json"; do
  test -s "${required}"
done

printf '%s  %s\n' \
  "48938400ae3464c9680731287f583a9cb516f55a8ec64ea13a91be47fb15b607" \
  "${PUSHT_SOURCE}/weights.pt" | sha256sum --check --strict
printf '%s  %s\n' \
  "2839a907362f403f9136383016e91774373a295d958ae75121791f22a9fddf89" \
  "${CUBE_SOURCE}/weights.pt" | sha256sum --check --strict

if [[ -e "${PUSHT_OUTPUT}" || -e "${CUBE_OUTPUT}" ]]; then
  echo "Refusing to overwrite an existing versioned converted checkpoint" >&2
  exit 2
fi

mkdir -p "${PROVENANCE}" "${JOB_TMP}/apptainer"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"

echo "job_id=${SLURM_JOB_ID}"
echo "node=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

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
      --weights "'"${PUSHT_SOURCE}"'/weights.pt" \
      --config "'"${PUSHT_SOURCE}"'/config.json" \
      --run-name pusht/lewm_hf_22b330c \
      --cache-dir "'"${STABLEWM_HOME}"'"

    python "'"${CODE}"'/scripts/tools/convert_hf_weights_to_object_ckpt.py" \
      --weights "'"${CUBE_SOURCE}"'/weights.pt" \
      --config "'"${CUBE_SOURCE}"'/config.json" \
      --run-name cube/lewm_hf_b0747c5 \
      --cache-dir "'"${STABLEWM_HOME}"'"
  '

test -s "${PUSHT_OUTPUT}"
test -s "${CUBE_OUTPUT}"
sha256sum \
  "${PUSHT_SOURCE}/config.json" "${PUSHT_SOURCE}/weights.pt" "${PUSHT_OUTPUT}" \
  "${CUBE_SOURCE}/config.json" "${CUBE_SOURCE}/weights.pt" "${CUBE_OUTPUT}" \
  > "${PROVENANCE}/sha256.txt"
printf '%s\n' \
  "pusht_repo=quentinll/lewm-pusht" \
  "pusht_revision=22b330c28c27ead4bfd1888615af1340e3fe9052" \
  "cube_repo=quentinll/lewm-cube" \
  "cube_revision=b0747c5002e86d2ce8f3cd8178004b97524c587d" \
  "strict_state_dict_load=true" \
  "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "${PROVENANCE}/provenance.txt"
cat "${PROVENANCE}/sha256.txt"
