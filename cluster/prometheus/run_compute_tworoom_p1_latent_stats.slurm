#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p1-latent-stats
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p1-latent-stats-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p1-latent-stats-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/compute_p1_latent_stats.py"
RUNNER="${ROOT}/scripts/run_compute_tworoom_p1_latent_stats.slurm"
LATENT_ROOT="${ROOT}/data/stablewm/derived/latents/hi-lewm-tworoom-epoch15"
LATENT_DIR="${LATENT_ROOT}/p1"
PARTITION_DIR="${ROOT}/manifests/partitions/tworoom-v1"
OUTPUT_DIR="${LATENT_ROOT}/p1-train-stats-job-${SLURM_JOB_ID}"
CANONICAL_DIR="${LATENT_ROOT}/p1-train-stats"
JOB_TMP="/tmp/ckontzias-tworoom-p1-stats-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="014c25f51ac0c11c80503df4d23f06beb382e968e5f5c752c59fcf5c89ff7b2c"
EXPECTED_MASTER_SHA256="47971097b1979798345c298d91eb36f91a0884353789b7f8736e6a1f9e79f790"
EXPECTED_SPLIT_SHA256="256dce7f81d30d562039395fdc4680c218c4f4ffe513f690e9c360c601d0ffa3"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
  "${LATENT_DIR}/checksums.sha256" \
  "${PARTITION_DIR}/episodes-seed-20260728.tsv" \
  "${PARTITION_DIR}/p1-train-val-seed-20260728.tsv"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom P1-statistics input: ${required}" >&2; exit 2; fi
done
if [[ ! -L "${LATENT_DIR}" ]]; then echo "TwoRoom P1 cache is not the canonical symlink" >&2; exit 2; fi
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_MASTER_SHA256}  ${PARTITION_DIR}/episodes-seed-20260728.tsv" | sha256sum -c -
echo "${EXPECTED_SPLIT_SHA256}  ${PARTITION_DIR}/p1-train-val-seed-20260728.tsv" | sha256sum -c -
sha256sum -c "${LATENT_DIR}/checksums.sha256"
if [[ -e "${OUTPUT_DIR}" || -e "${CANONICAL_DIR}" ]]; then
  echo "Refusing to overwrite TwoRoom P1 statistics or canonical link" >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p1_train_latent_standardization"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "canonical_latent_target=$(readlink -f "${LATENT_DIR}")"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
    "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
    "${LATENT_DIR}/checksums.sha256" \
    "${PARTITION_DIR}/episodes-seed-20260728.tsv" \
    "${PARTITION_DIR}/p1-train-val-seed-20260728.tsv"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --master-partition-manifest "'"${PARTITION_DIR}"'/episodes-seed-20260728.tsv" \
      --p1-split-manifest "'"${PARTITION_DIR}"'/p1-train-val-seed-20260728.tsv" \
      --output-npz "'"${OUTPUT_DIR}"'/stats.npz" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --std-floor 1e-6
  '

test -s "${OUTPUT_DIR}/stats.npz"
test -s "${OUTPUT_DIR}/manifest.json"
grep -q '"status": "ok"' "${OUTPUT_DIR}/manifest.json"
grep -q '"count": 573858' "${OUTPUT_DIR}/manifest.json"
grep -q '"latent_dim": 192' "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
ln -s -- "${OUTPUT_DIR}" "${CANONICAL_DIR}"
