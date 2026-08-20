#!/usr/bin/env bash

# Submit with P3_LABEL_JOB_ID and an afterok dependency on both the P3 label
# job and the independently aggregated P3 real-frame agreement audit.

#SBATCH --job-name=p3-score-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p3-score-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p3-score-audit-%j.err

set -euo pipefail
: "${P3_LABEL_JOB_ID:?submit with P3_LABEL_JOB_ID set to the locked P3 label job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/score_and_evaluate_p3_locked_scorers.py"
RUNNER="${ROOT}/scripts/run_score_and_evaluate_p3_locked_scorers.slurm"
LOCK="${ROOT}/protocol/P3-PRE-EXECUTION-LOCK-2026-08-09.md"
LOCK_SHA256="a9f5c93bea7562c9f83c97c74f1cbf6041772626f3abd4d20fcd236a0b385d35"
STABLEWM_HOME="${ROOT}/data/stablewm"
P3_LABELED_DIR="${STABLEWM_HOME}/derived/candidate-labels/pusht-v1/p3-stratum3-job-${P3_LABEL_JOB_ID}"
P2_TRUE_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-true-selection-job-294839"
P2_CALIBRATION_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p2-null-control-calibration-job-294843"
M1_ROOT="${STABLEWM_HOME}/runs/scorers/m1/pusht-v1"
M2_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-pusht-v1"
M3_ROOT="${STABLEWM_HOME}/derived/scorers/m3-trm-pusht-v1"
AUTOENCODER_ROOT="${STABLEWM_HOME}/derived/scorers/m2-autoencoder-pusht-v1"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
OUTPUT_DIR="${STABLEWM_HOME}/derived/scorer-audits/pusht-v1/p3-locked-audit-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p3-score-audit-${SLURM_JOB_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}"
  "${P3_LABELED_DIR}/labeled-candidates.h5" "${P3_LABELED_DIR}/manifest.json" "${P3_LABELED_DIR}/checksums.sha256"
  "${P2_TRUE_DIR}/scores.h5" "${P2_TRUE_DIR}/manifest.json" "${P2_TRUE_DIR}/checksums.sha256"
  "${P2_CALIBRATION_DIR}/audit-and-calibrators.h5" "${P2_CALIBRATION_DIR}/manifest.json" "${P2_CALIBRATION_DIR}/checksums.sha256"
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${NOISE_DIR}/checksums.sha256"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing or empty required input: ${required}" >&2; exit 2; fi
done
for required_dir in "${M1_ROOT}" "${M2_ROOT}" "${M3_ROOT}" "${AUTOENCODER_ROOT}"; do
  if [[ ! -d "${required_dir}" ]]; then echo "Missing scorer root: ${required_dir}" >&2; exit 2; fi
done
echo "${LOCK_SHA256}  ${LOCK}" | sha256sum -c - >/dev/null
(cd "${P3_LABELED_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${P2_TRUE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${P2_CALIBRATION_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${NOISE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite locked P3 scorer audit: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=p3_locked_scorer_audit_and_promotion"
  echo "p3_label_job_id=${P3_LABEL_JOB_ID}"
  echo "p2_true_score_job_id=294839"
  echo "p2_calibration_job_id=294843"
  echo "null_training_job_id=294841"
  echo "autoencoder_training_job_id=294842"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}" \
    "${P3_LABELED_DIR}/labeled-candidates.h5" "${P3_LABELED_DIR}/manifest.json" \
    "${P2_TRUE_DIR}/scores.h5" "${P2_TRUE_DIR}/manifest.json" \
    "${P2_CALIBRATION_DIR}/audit-and-calibrators.h5" "${P2_CALIBRATION_DIR}/manifest.json" \
    "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=20260728
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --p3-labeled-dir "'"${P3_LABELED_DIR}"'" \
      --p2-true-score-dir "'"${P2_TRUE_DIR}"'" \
      --p2-calibration-dir "'"${P2_CALIBRATION_DIR}"'" \
      --m1-root "'"${M1_ROOT}"'" \
      --m2-root "'"${M2_ROOT}"'" \
      --m3-root "'"${M3_ROOT}"'" \
      --autoencoder-root "'"${AUTOENCODER_ROOT}"'" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" \
      --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/audit.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --device cuda --m2-batch-size 2048
  '

test -s "${OUTPUT_DIR}/audit.h5"; test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
