#!/usr/bin/env bash

# Submit after the full array with --export=ALL,INPUT_ARRAY_JOB_ID=<array job>.

#SBATCH --job-name=p3-subgoal-aggregate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p3-subgoal-aggregate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p3-subgoal-aggregate-%j.err

set -euo pipefail
: "${INPUT_ARRAY_JOB_ID:?submit with INPUT_ARRAY_JOB_ID set to the P3 fixed-subgoal execution array}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/aggregate_p2_fixed_subgoal_executions.py"
RUNNER="${ROOT}/scripts/run_aggregate_p3_fixed_subgoal_executions.slurm"
LOCK="${ROOT}/protocol/P3-PRE-EXECUTION-LOCK-2026-08-09.md"
LOCK_SHA256="a9f5c93bea7562c9f83c97c74f1cbf6041772626f3abd4d20fcd236a0b385d35"
STABLEWM_HOME="${ROOT}/data/stablewm"
EXECUTION_ROOT="${STABLEWM_HOME}/derived/candidate-executions/pusht-v1/p3-stratum3-job-${INPUT_ARRAY_JOB_ID}"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/pusht-v1/p3-stratum3-b0-d75-h2-job-294828"
OUTPUT_DIR="${STABLEWM_HOME}/derived/candidate-executions/pusht-v1/p3-stratum3-aggregate-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p3-subgoal-aggregate-${SLURM_JOB_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}" "${EXECUTION_ROOT}"
  "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -e "${required}" ]]; then echo "Missing required input: ${required}" >&2; exit 2; fi
done
echo "${LOCK_SHA256}  ${LOCK}" | sha256sum -c - >/dev/null
(cd "${CANDIDATE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite P3 execution aggregate: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=p3_stratum3_candidate_attainment_aggregate"
  echo "source_array_job_id=${INPUT_ARRAY_JOB_ID}"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LOCK}" \
    "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" \
    "${CANDIDATE_DIR}/checksums.sha256"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --partition P3 \
      --execution-root "'"${EXECUTION_ROOT}"'" \
      --candidate-h5 "'"${CANDIDATE_DIR}"'/candidate-pools.h5" \
      --candidate-manifest "'"${CANDIDATE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/aggregate.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/aggregate.h5"; test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
