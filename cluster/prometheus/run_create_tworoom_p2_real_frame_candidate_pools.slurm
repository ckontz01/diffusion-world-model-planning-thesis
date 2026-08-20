#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p2-real-pools
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-real-pools-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-real-pools-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/create_p2_real_frame_candidate_pools.py"
RUNNER="${ROOT}/scripts/run_create_tworoom_p2_real_frame_candidate_pools.slurm"
STABLEWM_HOME="${ROOT}/data/stablewm"
PARTITION_MANIFEST="${ROOT}/manifests/partitions/tworoom-v1/episodes-seed-20260728.tsv"
LATENT_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-tworoom-epoch15/p2"
DATASET="${STABLEWM_HOME}/tworoom.h5"
CANDIDATE_ROOT="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1"
OUTPUT_DIR="${CANDIDATE_ROOT}/p2-real-frame-job-${SLURM_JOB_ID}"
CANONICAL_DIR="${CANDIDATE_ROOT}/p2-real-frame"
JOB_TMP="/tmp/ckontzias-tworoom-p2-real-pools-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="5a1ca3c7b4f604e279e796e40c88f96ba262f4db3816acc615204f10b433cfa8"
EXPECTED_DATASET_SHA256="129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623"
EXPECTED_PARTITIONS_SHA256="47971097b1979798345c298d91eb36f91a0884353789b7f8736e6a1f9e79f790"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${PARTITION_MANIFEST}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
  "${LATENT_DIR}/checksums.sha256" "${DATASET}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom P2 real-pool input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_DATASET_SHA256}  ${DATASET}" | sha256sum -c -
echo "${EXPECTED_PARTITIONS_SHA256}  ${PARTITION_MANIFEST}" | sha256sum -c -
(cd "${LATENT_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" || -e "${CANONICAL_DIR}" ]]; then
  echo "Refusing to overwrite TwoRoom P2 real-frame pools or canonical link" >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p2_real_frame_candidate_pool_creation"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${PARTITION_MANIFEST}" \
    "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
    "${LATENT_DIR}/checksums.sha256" "${DATASET}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --environment tworoom --partition P2 \
      --partition-manifest "'"${PARTITION_MANIFEST}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --dataset "'"${DATASET}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/candidate-pools.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --seed 20260728 --pools-per-stratum 12 --candidates-per-pool 64 --delta 25
  '

test -s "${OUTPUT_DIR}/candidate-pools.h5"
test -s "${OUTPUT_DIR}/manifest.json"
grep -q '"classification": "tworoom_p2_real_frame_candidate_pools"' "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
ln -s -- "${OUTPUT_DIR}" "${CANONICAL_DIR}"
