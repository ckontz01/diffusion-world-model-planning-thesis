#!/usr/bin/env bash

# Frozen exploratory PushT M2 conditioning-use diagnostic (P1/P2 only).

#SBATCH --job-name=m2-cond-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=20G
#SBATCH --time=00:45:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-cond-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2-cond-audit-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/audit_m2_conditioning_use.py"
TRAIN_SCRIPT="${ROOT}/scripts/train_m2_diffusion_head.py"
RUNNER="${ROOT}/scripts/run_audit_m2_conditioning_use.slurm"
SPEC="${ROOT}/protocol/PUSHT-M2-CONDITIONING-AUDIT-SPEC-2026-08-12.md"
SPEC_SHA256="3a6ab0966f67f8ee251f997a1c00ea573555bdc4a2055f79320ac792984b865a"
DATA="${ROOT}/data/stablewm"
LATENT_DIR="${DATA}/derived/latents/hi-lewm-pusht-epoch15/p1-job-294589"
STATS_DIR="${DATA}/derived/latents/hi-lewm-pusht-epoch15/p1-train-stats-job-294596"
PAIR_PLAN="${ROOT}/manifests/partitions/pusht-v1/scorer-pairs-seed-20260728/m1-m2-all-delta25-episodes.tsv"
LABELED_DIR="${DATA}/derived/candidate-labels/pusht-v1/p2-stratum3-job-294838"
SELECTION_DIR="${DATA}/derived/scorer-audits/pusht-v1/p2-true-selection-job-294839"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
M2_ROOT="${DATA}/derived/scorers/m2-diffusion-pusht-v1/true/width-1024"
CHECKPOINTS=(
  "${M2_ROOT}/seed-20260728-job-294599-3/best-checkpoint.pt"
  "${M2_ROOT}/seed-20260729-job-294599-4/best-checkpoint.pt"
  "${M2_ROOT}/seed-20260730-job-294599-5/best-checkpoint.pt"
)
OUTPUT_DIR="${DATA}/derived/scorer-audits/pusht-v1/m2-conditioning-audit-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m2-conditioning-audit-${SLURM_JOB_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${TRAIN_SCRIPT}" "${RUNNER}" "${SPEC}"
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json"
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${PAIR_PLAN}"
  "${LABELED_DIR}/labeled-candidates.h5" "${LABELED_DIR}/manifest.json"
  "${SELECTION_DIR}/scores.h5" "${SELECTION_DIR}/manifest.json"
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${CHECKPOINTS[@]}"
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
  echo "classification=pusht_m2_conditioning_use_audit"
  echo "partition_scope=P1-validation-and-P2-development-only"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${TRAIN_SCRIPT}" "${RUNNER}" "${SPEC}" \
    "${LATENT_DIR}/manifest.json" "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" \
    "${PAIR_PLAN}" "${LABELED_DIR}/manifest.json" "${SELECTION_DIR}/manifest.json" \
    "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${CHECKPOINTS[@]}"
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
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --pair-plan "'"${PAIR_PLAN}"'" \
      --stats-npz "'"${STATS_DIR}"'/stats.npz" \
      --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --checkpoint "'"${CHECKPOINTS[0]}"'" \
      --checkpoint "'"${CHECKPOINTS[1]}"'" \
      --checkpoint "'"${CHECKPOINTS[2]}"'" \
      --labeled-dir "'"${LABELED_DIR}"'" \
      --selection-dir "'"${SELECTION_DIR}"'" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" \
      --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --spec "'"${SPEC}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/conditioning-audit.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --device cuda \
      --batch-size 2048
  '

test -s "${OUTPUT_DIR}/conditioning-audit.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
