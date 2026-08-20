#!/usr/bin/env bash

# Frozen M2v2 offline P2 candidate-pool diagnostic, one task per environment.

#SBATCH --job-name=m2v2-p2-offline
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --array=0-1%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2v2-p2-offline-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2v2-p2-offline-%A_%a.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/audit_m2v2_p2_offline.py"
SCORER="${ROOT}/scripts/m2v2_likelihood_ratio.py"
SHARED="${ROOT}/scripts/audit_candidate_pool_ranking.py"
RUNNER="${ROOT}/scripts/run_audit_m2v2_p2_offline_array.slurm"
SPEC="${ROOT}/protocol/M2V2-P1-P2-FEASIBILITY-SPEC-2026-08-12.md"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
: "${SPEC_SHA256:?submit with frozen SPEC_SHA256}"
: "${UNCONDITIONAL_JOB_ID:?submit with M2v2 unconditional job ID}"
: "${REFERENCE_JOB_ID:?submit with completed M2v2 P1-reference job ID}"

SEEDS=(20260728 20260729 20260730)
if (( SLURM_ARRAY_TASK_ID == 0 )); then
  ENVIRONMENT="pusht"
  CONDITIONAL_ROOT="${ROOT}/data/stablewm/derived/scorers/m2-diffusion-pusht-v1/true/width-1024"
  CONDITIONAL_JOB_ID=294599
  UNCONDITIONAL_TASK_OFFSET=0
  LABELED_DIR="${ROOT}/data/stablewm/derived/candidate-labels/pusht-v1/p2-stratum3-job-294838"
  TRUE_DIR="${ROOT}/data/stablewm/derived/scorer-audits/pusht-v1/p2-true-selection-job-294839"
else
  ENVIRONMENT="tworoom"
  CONDITIONAL_ROOT="${ROOT}/data/stablewm/derived/scorers/m2-diffusion-tworoom-v1/true/width-1024"
  CONDITIONAL_JOB_ID=295652
  UNCONDITIONAL_TASK_OFFSET=3
  LABELED_DIR="${ROOT}/data/stablewm/derived/candidate-audits/tworoom-v1/p2-stratum3-labeled-job-295868"
  TRUE_DIR="${ROOT}/data/stablewm/derived/scorer-audits/tworoom-v1/p2-true-selection-job-295869"
fi
UNCONDITIONAL_ROOT="${ROOT}/data/stablewm/derived/scorers/m2v2-unconditional-${ENVIRONMENT}-v1/width-1024"
REFERENCE_DIR="${ROOT}/data/stablewm/derived/scorer-audits/${ENVIRONMENT}-v1/m2v2-p1-reference-job-${REFERENCE_JOB_ID}"
OUTPUT_DIR="${ROOT}/data/stablewm/derived/scorer-audits/${ENVIRONMENT}-v1/m2v2-p2-offline-job-${SLURM_ARRAY_JOB_ID}"
JOB_TMP="/tmp/ckontzias-m2v2-p2-offline-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

CONDITIONAL_ARGS=()
UNCONDITIONAL_ARGS=()
CHECKPOINTS=()
for seed_index in 0 1 2; do
  seed="${SEEDS[seed_index]}"
  conditional_task=$((seed_index + 3))
  unconditional_task=$((seed_index + UNCONDITIONAL_TASK_OFFSET))
  conditional="${CONDITIONAL_ROOT}/seed-${seed}-job-${CONDITIONAL_JOB_ID}-${conditional_task}/best-checkpoint.pt"
  unconditional="${UNCONDITIONAL_ROOT}/seed-${seed}-job-${UNCONDITIONAL_JOB_ID}-${unconditional_task}/best-checkpoint.pt"
  CONDITIONAL_ARGS+=(--conditional-checkpoint "${conditional}")
  UNCONDITIONAL_ARGS+=(--unconditional-checkpoint "${unconditional}")
  CHECKPOINTS+=("${conditional}" "${unconditional}")
done
for required in "${IMAGE}" "${SCRIPT}" "${SCORER}" "${SHARED}" "${RUNNER}" "${SPEC}" \
  "${LABELED_DIR}/labeled-candidates.h5" "${LABELED_DIR}/manifest.json" \
  "${TRUE_DIR}/scores.h5" "${TRUE_DIR}/manifest.json" \
  "${REFERENCE_DIR}/reference.npz" "${REFERENCE_DIR}/manifest.json" \
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${CHECKPOINTS[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing M2v2 offline input: ${required}" >&2; exit 2; fi
done
echo "${SPEC_SHA256}  ${SPEC}" | sha256sum -c - >/dev/null
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite M2v2 offline output" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
{
  echo "classification=${ENVIRONMENT}_m2v2_p2_offline_within_pool_audit"
  echo "partition=P2-development-only"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${SCORER}" "${SHARED}" "${RUNNER}" "${SPEC}" \
    "${LABELED_DIR}/labeled-candidates.h5" "${LABELED_DIR}/manifest.json" \
    "${TRUE_DIR}/scores.h5" "${TRUE_DIR}/manifest.json" \
    "${REFERENCE_DIR}/reference.npz" "${REFERENCE_DIR}/manifest.json" \
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
    python "'"${SCRIPT}"'" --environment "'"${ENVIRONMENT}"'" \
      --labeled-dir "'"${LABELED_DIR}"'" --true-selection-dir "'"${TRUE_DIR}"'" \
      '"${CONDITIONAL_ARGS[*]}"' '"${UNCONDITIONAL_ARGS[*]}"' \
      --reference-npz "'"${REFERENCE_DIR}"'/reference.npz" \
      --reference-manifest "'"${REFERENCE_DIR}"'/manifest.json" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --spec "'"${SPEC}"'" --output-dir "'"${OUTPUT_DIR}"'"
  '

test -s "${OUTPUT_DIR}/audit.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
