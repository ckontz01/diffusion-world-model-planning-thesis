#!/usr/bin/env bash

# P2-only real-frame reachability audit for the selected PushT M2.

#SBATCH --job-name=m2-real-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-real-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-real-audit-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/audit_m2_real_frame_pairs.py"
RUNNER="${ROOT}/scripts/run_audit_m2_real_frame_pairs.slurm"
SPEC="${ROOT}/protocol/PUSHT-M2-REAL-FRAME-AUDIT-SPEC-2026-08-12.md"
SPEC_SHA256="8c774161d8ea6b93cad47a6a9526f9dacf316fb891052fa0393d821ca03e06b8"
DATA="${ROOT}/data/stablewm"
AGGREGATE_DIR="${DATA}/derived/candidate-executions/pusht-v1/p2-real-frame-aggregate-job-294668"
STATS_DIR="${DATA}/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596"
SELECTION_DIR="${DATA}/derived/scorer-audits/pusht-v1/p2-true-selection-job-294839"
CALIBRATION_DIR="${DATA}/derived/scorer-audits/pusht-v1/p2-null-control-calibration-job-294843"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
TRUE_ROOT="${DATA}/derived/scorers/m2-diffusion-pusht-v1/true/width-1024"
NULL_ROOT="${DATA}/derived/scorers/m2-diffusion-pusht-v1/mismatched/width-1024"
AE_ROOT="${DATA}/derived/scorers/m2-autoencoder-pusht-v1/width-1024"
TRUE_CHECKPOINTS=(
  "${TRUE_ROOT}/seed-20260728-job-294599-3/best-checkpoint.pt"
  "${TRUE_ROOT}/seed-20260729-job-294599-4/best-checkpoint.pt"
  "${TRUE_ROOT}/seed-20260730-job-294599-5/best-checkpoint.pt"
)
NULL_CHECKPOINTS=(
  "${NULL_ROOT}/seed-20260728-job-294841-3/best-checkpoint.pt"
  "${NULL_ROOT}/seed-20260729-job-294841-4/best-checkpoint.pt"
  "${NULL_ROOT}/seed-20260730-job-294841-5/best-checkpoint.pt"
)
AE_CHECKPOINTS=(
  "${AE_ROOT}/seed-20260728-job-294842-0/best-checkpoint.pt"
  "${AE_ROOT}/seed-20260729-job-294842-1/best-checkpoint.pt"
  "${AE_ROOT}/seed-20260730-job-294842-2/best-checkpoint.pt"
)
OUTPUT_DIR="${DATA}/derived/scorer-audits/pusht-v1/m2-real-frame-audit-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m2-real-frame-audit-${SLURM_JOB_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${SPEC}"
  "${AGGREGATE_DIR}/aggregate.h5" "${AGGREGATE_DIR}/manifest.json"
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json"
  "${SELECTION_DIR}/manifest.json" "${CALIBRATION_DIR}/manifest.json"
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json"
  "${TRUE_CHECKPOINTS[@]}" "${NULL_CHECKPOINTS[@]}" "${AE_CHECKPOINTS[@]}"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty input: ${required}" >&2; exit 2; fi
done
echo "${SPEC_SHA256}  ${SPEC}" | sha256sum -c - >/dev/null
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=pusht_m2_real_frame_reachability_audit"
  echo "partition_scope=P2-development-only"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${SPEC}" \
    "${AGGREGATE_DIR}/aggregate.h5" "${AGGREGATE_DIR}/manifest.json" \
    "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" \
    "${SELECTION_DIR}/manifest.json" "${CALIBRATION_DIR}/manifest.json" \
    "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" \
    "${TRUE_CHECKPOINTS[@]}" "${NULL_CHECKPOINTS[@]}" "${AE_CHECKPOINTS[@]}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=20260812
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --aggregate-h5 "'"${AGGREGATE_DIR}"'/aggregate.h5" \
      --aggregate-manifest "'"${AGGREGATE_DIR}"'/manifest.json" \
      --stats-npz "'"${STATS_DIR}"'/stats.npz" \
      --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --selection-manifest "'"${SELECTION_DIR}"'/manifest.json" \
      --calibration-manifest "'"${CALIBRATION_DIR}"'/manifest.json" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" \
      --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --true-checkpoint "'"${TRUE_CHECKPOINTS[0]}"'" \
      --true-checkpoint "'"${TRUE_CHECKPOINTS[1]}"'" \
      --true-checkpoint "'"${TRUE_CHECKPOINTS[2]}"'" \
      --null-checkpoint "'"${NULL_CHECKPOINTS[0]}"'" \
      --null-checkpoint "'"${NULL_CHECKPOINTS[1]}"'" \
      --null-checkpoint "'"${NULL_CHECKPOINTS[2]}"'" \
      --autoencoder-checkpoint "'"${AE_CHECKPOINTS[0]}"'" \
      --autoencoder-checkpoint "'"${AE_CHECKPOINTS[1]}"'" \
      --autoencoder-checkpoint "'"${AE_CHECKPOINTS[2]}"'" \
      --spec "'"${SPEC}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/real-frame-audit.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --device cuda \
      --batch-size 2048
  '

test -s "${OUTPUT_DIR}/real-frame-audit.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
