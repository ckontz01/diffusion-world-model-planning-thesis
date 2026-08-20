#!/usr/bin/env bash

#SBATCH --job-name=tworoom-m3-heads
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --array=0-5%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m3-train-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m3-train-%A_%a.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/train_m3_temporal_head.py"
RUNNER="${ROOT}/scripts/run_tworoom_m3_temporal_head_array.slurm"
LATENT_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-tworoom-epoch15/p1"
PAIR_DIR="${ROOT}/manifests/partitions/tworoom-v1/scorer-pairs-seed-20260728"
PAIR_MANIFEST="${PAIR_DIR}/m3-balanced-delta1-40.tsv.gz"
PAIR_SUMMARY="${PAIR_DIR}/scorer-pair-manifests-summary.json"

EXPECTED_SCRIPT_SHA256="8ab0124a858e8c4f3bb1f47c5020eda0adff2cbd93221ad87c22d1d85144e854"
EXPECTED_PAIR_SHA256="f1bccba16113e81ed581ce237023c522f5229cf4f023afe32c0904b628a6b5d7"
EXPECTED_SUMMARY_SHA256="7ec2df8dda66ea9f8fb0b0b9457533486e7d47eea40ccf8295a31abff284e94d"

SEEDS=(20260728 20260729 20260730)
if (( SLURM_ARRAY_TASK_ID < 3 )); then
  CONDITION="true"
  SEED_INDEX="${SLURM_ARRAY_TASK_ID}"
else
  CONDITION="shuffled"
  SEED_INDEX="$((SLURM_ARRAY_TASK_ID - 3))"
fi
TRAINING_SEED="${SEEDS[SEED_INDEX]}"
OUTPUT_DIR="${ROOT}/data/stablewm/derived/scorers/m3-trm-tworoom-v1/${CONDITION}/seed-${TRAINING_SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-m3-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
  "${LATENT_DIR}/checksums.sha256" "${PAIR_MANIFEST}" "${PAIR_SUMMARY}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom M3 input: ${required}" >&2; exit 2; fi
done
if [[ ! -L "${LATENT_DIR}" ]]; then echo "TwoRoom P1 cache is not canonical" >&2; exit 2; fi
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_PAIR_SHA256}  ${PAIR_MANIFEST}" | sha256sum -c -
echo "${EXPECTED_SUMMARY_SHA256}  ${PAIR_SUMMARY}" | sha256sum -c -
sha256sum -c "${LATENT_DIR}/checksums.sha256"
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite TwoRoom M3 output" >&2; exit 2; fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_m3_temporal_reachability_head"
  echo "condition=${CONDITION}"
  echo "training_seed=${TRAINING_SEED}"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "canonical_latent_target=$(readlink -f "${LATENT_DIR}")"
  sha256sum "${IMAGE}" "${RUNNER}" "${SCRIPT}" \
    "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" \
    "${PAIR_MANIFEST}" "${PAIR_SUMMARY}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED="'"${TRAINING_SEED}"'"
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --pair-manifest "'"${PAIR_MANIFEST}"'" \
      --pair-summary "'"${PAIR_SUMMARY}"'" \
      --output-dir "'"${OUTPUT_DIR}"'" \
      --condition "'"${CONDITION}"'" \
      --seed "'"${TRAINING_SEED}"'" \
      --device cuda
  '

test -s "${OUTPUT_DIR}/best-checkpoint.pt"
test -s "${OUTPUT_DIR}/training-result.json"
grep -q '"status": "ok"' "${OUTPUT_DIR}/training-result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
