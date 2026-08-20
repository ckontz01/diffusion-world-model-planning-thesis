#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p2-null-calibrate
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-null-calibrate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-null-calibrate-%j.err

set -euo pipefail
: "${LABELED_JOB_ID:?submit with LABELED_JOB_ID set to the completed TwoRoom P2 labeling job}"
: "${TRUE_SCORE_JOB_ID:?submit with TRUE_SCORE_JOB_ID set to the completed TwoRoom P2 true-scorer selection job}"
: "${NULL_TRAINING_JOB_ID:?submit with NULL_TRAINING_JOB_ID set to the completed TwoRoom null-training array job}"
: "${AUTOENCODER_TRAINING_JOB_ID:?submit with AUTOENCODER_TRAINING_JOB_ID set to the completed TwoRoom autoencoder-training array job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/score_nulls_autoencoder_and_fit_p2_calibrators.py"
TRUE_SCORE_SCRIPT="${ROOT}/scripts/score_and_select_p2_true_scorers.py"
M1_SCRIPT="${ROOT}/scripts/train_m1_macro_cycle_head.py"
M2_SCRIPT="${ROOT}/scripts/train_m2_diffusion_head.py"
AE_SCRIPT="${ROOT}/scripts/train_m2_autoencoder_control.py"
RUNNER="${ROOT}/scripts/run_score_tworoom_nulls_autoencoder_and_fit_p2_calibrators.slurm"
STABLEWM_HOME="${ROOT}/data/stablewm"
LABELED_DIR="${STABLEWM_HOME}/derived/candidate-audits/tworoom-v1/p2-stratum3-labeled-job-${LABELED_JOB_ID}"
TRUE_SCORE_DIR="${STABLEWM_HOME}/derived/scorer-audits/tworoom-v1/p2-true-selection-job-${TRUE_SCORE_JOB_ID}"
M1_ROOT="${STABLEWM_HOME}/runs/scorers/m1/tworoom-v1"
M2_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-tworoom-v1"
AUTOENCODER_ROOT="${STABLEWM_HOME}/derived/scorers/m2-autoencoder-tworoom-v1"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
AUDIT_ROOT="${STABLEWM_HOME}/derived/scorer-audits/tworoom-v1"
OUTPUT_DIR="${AUDIT_ROOT}/p2-null-control-calibration-job-${SLURM_JOB_ID}"
CANONICAL_DIR="${AUDIT_ROOT}/p2-null-control-calibration"
JOB_TMP="/tmp/ckontzias-tworoom-p2-null-calibrate-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="991528668f89bd653339296f9fbe88e179a5011f6d7a973d93cb7e7ac30270e9"
EXPECTED_TRUE_SCORE_SCRIPT_SHA256="57be0645a9e7a671a40a18d23994e3ff04a7af0f8c0a445eba726d3925ba141d"
EXPECTED_M1_SCRIPT_SHA256="e7baf8d66bd77d53a49164592ecdc16e9b1f50b1f86baa473467ba2de9327733"
EXPECTED_M2_SCRIPT_SHA256="f74f12c945d7542f9af0e8ea0f96247b3beb6338869ab0d0589f7b10a2f69efd"
EXPECTED_AE_SCRIPT_SHA256="d744791aef0e6ca0c68ee023ea87d45c1e29ab15973aa0525c2b12f49b5172f3"
EXPECTED_NOISE_SHA256="3a94b491079e6030137480352d1ac0d985214db6ebd96f271539b2022edcf74b"
EXPECTED_NOISE_MANIFEST_SHA256="9723272e798a6d40b54caaa8529d83afa90dcc62f621141c3fc12eba761d5deb"

for required in "${IMAGE}" "${SCRIPT}" "${TRUE_SCORE_SCRIPT}" "${M1_SCRIPT}" \
  "${M2_SCRIPT}" "${AE_SCRIPT}" "${RUNNER}" \
  "${LABELED_DIR}/labeled-candidates.h5" "${LABELED_DIR}/manifest.json" "${LABELED_DIR}/checksums.sha256" \
  "${TRUE_SCORE_DIR}/scores.h5" "${TRUE_SCORE_DIR}/manifest.json" "${TRUE_SCORE_DIR}/checksums.sha256" \
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${NOISE_DIR}/checksums.sha256"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom calibration input: ${required}" >&2; exit 2; fi
done
for required_dir in "${M1_ROOT}" "${M2_ROOT}" "${AUTOENCODER_ROOT}"; do
  if [[ ! -d "${required_dir}" ]]; then echo "Missing TwoRoom scorer root: ${required_dir}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_TRUE_SCORE_SCRIPT_SHA256}  ${TRUE_SCORE_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_M1_SCRIPT_SHA256}  ${M1_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_M2_SCRIPT_SHA256}  ${M2_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_AE_SCRIPT_SHA256}  ${AE_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_NOISE_SHA256}  ${NOISE_DIR}/noise.npy" | sha256sum -c -
echo "${EXPECTED_NOISE_MANIFEST_SHA256}  ${NOISE_DIR}/manifest.json" | sha256sum -c -
sha256sum -c "${LABELED_DIR}/checksums.sha256" >/dev/null
sha256sum -c "${TRUE_SCORE_DIR}/checksums.sha256" >/dev/null
sha256sum -c "${NOISE_DIR}/checksums.sha256" >/dev/null
if [[ -e "${OUTPUT_DIR}" || -e "${CANONICAL_DIR}" ]]; then
  echo "Refusing to overwrite TwoRoom P2 null/control/calibration output" >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p2_null_control_scores_and_calibrators"
  echo "labeled_job_id=${LABELED_JOB_ID}"
  echo "true_score_job_id=${TRUE_SCORE_JOB_ID}"
  echo "null_training_job_id=${NULL_TRAINING_JOB_ID}"
  echo "autoencoder_training_job_id=${AUTOENCODER_TRAINING_JOB_ID}"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${TRUE_SCORE_SCRIPT}" "${M1_SCRIPT}" \
    "${M2_SCRIPT}" "${AE_SCRIPT}" "${RUNNER}" \
    "${LABELED_DIR}/manifest.json" "${LABELED_DIR}/checksums.sha256" \
    "${TRUE_SCORE_DIR}/manifest.json" "${TRUE_SCORE_DIR}/checksums.sha256" \
    "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${NOISE_DIR}/checksums.sha256"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=20260728
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --environment tworoom \
      --labeled-dir "'"${LABELED_DIR}"'" \
      --true-score-dir "'"${TRUE_SCORE_DIR}"'" \
      --m1-root "'"${M1_ROOT}"'" \
      --m2-root "'"${M2_ROOT}"'" \
      --autoencoder-root "'"${AUTOENCODER_ROOT}"'" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" \
      --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/audit-and-calibrators.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --null-job-id "'"${NULL_TRAINING_JOB_ID}"'" \
      --autoencoder-job-id "'"${AUTOENCODER_TRAINING_JOB_ID}"'" \
      --device cuda --m2-batch-size 2048
  '

test -s "${OUTPUT_DIR}/audit-and-calibrators.h5"
test -s "${OUTPUT_DIR}/manifest.json"
grep -q '"classification": "tworoom_p2_null_control_scores_and_calibrators"' "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
ln -s -- "${OUTPUT_DIR}" "${CANONICAL_DIR}"
