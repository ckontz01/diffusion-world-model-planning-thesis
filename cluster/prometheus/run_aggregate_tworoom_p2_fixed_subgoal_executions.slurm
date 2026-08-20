#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p2-subgoal-aggregate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-subgoal-aggregate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-subgoal-aggregate-%j.err

set -euo pipefail
: "${EXECUTION_ARRAY_JOB_ID:?submit with EXECUTION_ARRAY_JOB_ID set to the completed corrected imagined-subgoal array}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/aggregate_p2_fixed_subgoal_executions.py"
RUNNER="${ROOT}/scripts/run_aggregate_tworoom_p2_fixed_subgoal_executions.slurm"
STABLEWM_HOME="${ROOT}/data/stablewm"
EXECUTION_ROOT="${STABLEWM_HOME}/derived/candidate-executions/tworoom-v1/p2-stratum3-job-${EXECUTION_ARRAY_JOB_ID}"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1/p2-stratum3"
AUDIT_ROOT="${STABLEWM_HOME}/derived/candidate-audits/tworoom-v1"
OUTPUT_DIR="${AUDIT_ROOT}/p2-stratum3-aggregate-job-${SLURM_JOB_ID}"
CANONICAL_DIR="${AUDIT_ROOT}/p2-stratum3-aggregate"
JOB_TMP="/tmp/ckontzias-tworoom-p2-subgoal-aggregate-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="7479228a3670d062061da96cbf6c28db5dd82cb36db3728ad867943ed10f850c"
EXPECTED_CANDIDATE_SHA256="022a16c75bbcaf75a8ea77a98ea226ab7566a714d9b211ad5f9381f261285531"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${CANDIDATE_DIR}/candidate-pools.h5" \
  "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom subgoal-aggregate input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_CANDIDATE_SHA256}  ${CANDIDATE_DIR}/candidate-pools.h5" | sha256sum -c -
(cd "${CANDIDATE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ ! -d "${EXECUTION_ROOT}" ]]; then echo "Missing TwoRoom subgoal execution root" >&2; exit 2; fi
if [[ -e "${OUTPUT_DIR}" || -e "${CANONICAL_DIR}" ]]; then echo "Refusing to overwrite subgoal aggregate" >&2; exit 2; fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p2_stratum3_candidate_attainment_aggregation"
  echo "execution_array_job_id=${EXECUTION_ARRAY_JOB_ID}"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${CANDIDATE_DIR}/candidate-pools.h5" \
    "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" --environment tworoom --partition P2 \
      --execution-root "'"${EXECUTION_ROOT}"'" \
      --candidate-h5 "'"${CANDIDATE_DIR}"'/candidate-pools.h5" \
      --candidate-manifest "'"${CANDIDATE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/aggregate.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/aggregate.h5"
test -s "${OUTPUT_DIR}/manifest.json"
grep -q '"classification": "tworoom_p2_stratum3_candidate_attainment_aggregate"' "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
ln -s -- "${OUTPUT_DIR}" "${CANONICAL_DIR}"
