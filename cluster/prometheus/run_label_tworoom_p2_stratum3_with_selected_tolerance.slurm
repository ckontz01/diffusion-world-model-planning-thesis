#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p2-label-subgoals
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-label-subgoals-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-label-subgoals-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/label_p2_stratum3_with_selected_tolerance.py"
RUNNER="${ROOT}/scripts/run_label_tworoom_p2_stratum3_with_selected_tolerance.slurm"
STABLEWM_HOME="${ROOT}/data/stablewm"
AUDIT_ROOT="${STABLEWM_HOME}/derived/candidate-audits/tworoom-v1"
FIXED_DIR="${AUDIT_ROOT}/p2-stratum3-aggregate"
REAL_DIR="${AUDIT_ROOT}/p2-real-frame-aggregate"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1/p2-stratum3"
OUTPUT_DIR="${AUDIT_ROOT}/p2-stratum3-labeled-job-${SLURM_JOB_ID}"
CANONICAL_DIR="${AUDIT_ROOT}/p2-stratum3-labeled"
JOB_TMP="/tmp/ckontzias-tworoom-p2-label-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="5762e3df0b725a6235176ece7474c222974f017770d078404e59ceec4e22f3e7"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
  "${FIXED_DIR}/aggregate.h5" "${FIXED_DIR}/manifest.json" "${FIXED_DIR}/checksums.sha256" \
  "${REAL_DIR}/aggregate.h5" "${REAL_DIR}/manifest.json" "${REAL_DIR}/checksums.sha256" \
  "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom P2 labeling input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
(cd "${FIXED_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${REAL_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${CANDIDATE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" || -e "${CANONICAL_DIR}" ]]; then echo "Refusing to overwrite labeled audit" >&2; exit 2; fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p2_stratum3_selected_tolerance_labeling"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
    "${FIXED_DIR}/aggregate.h5" "${FIXED_DIR}/manifest.json" \
    "${REAL_DIR}/aggregate.h5" "${REAL_DIR}/manifest.json" \
    "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" --environment tworoom --partition P2 \
      --fixed-aggregate-dir "'"${FIXED_DIR}"'" --real-aggregate-dir "'"${REAL_DIR}"'" \
      --candidate-h5 "'"${CANDIDATE_DIR}"'/candidate-pools.h5" \
      --candidate-manifest "'"${CANDIDATE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/labeled-candidates.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/labeled-candidates.h5"
test -s "${OUTPUT_DIR}/manifest.json"
grep -q '"classification": "tworoom_p2_stratum3_labeled_candidate_audit"' "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
ln -s -- "${OUTPUT_DIR}" "${CANONICAL_DIR}"
