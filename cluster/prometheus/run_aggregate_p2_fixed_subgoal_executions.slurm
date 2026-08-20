#!/usr/bin/env bash

#SBATCH --job-name=p2-subgoal-aggregate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-subgoal-aggregate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/p2-subgoal-aggregate-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/aggregate_p2_fixed_subgoal_executions.py"
STABLEWM_HOME="${ROOT}/data/stablewm"
EXECUTION_ROOT="${STABLEWM_HOME}/derived/candidate-executions/pusht-v1/p2-stratum3-job-294652"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/pusht-v1/p2-stratum3-b0-d75-h2-job-294604"
OUTPUT_DIR="${STABLEWM_HOME}/derived/candidate-executions/pusht-v1/p2-stratum3-aggregate-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-p2-subgoal-aggregate-${SLURM_JOB_ID}"

REQUIRED=(
  "${EXECUTION_ROOT}"
  "${CANDIDATE_DIR}/candidate-pools.h5"
  "${CANDIDATE_DIR}/manifest.json"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -e "${required}" ]]; then
    echo "Missing required input: ${required}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite P2 execution aggregate: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

{
  echo "classification=p2_stratum3_candidate_attainment_aggregate"
  echo "source_array_job_id=294652"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${SCRIPT}" \
    "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --execution-root "'"${EXECUTION_ROOT}"'" \
      --candidate-h5 "'"${CANDIDATE_DIR}"'/candidate-pools.h5" \
      --candidate-manifest "'"${CANDIDATE_DIR}"'/manifest.json" \
      --output-h5 "'"${OUTPUT_DIR}"'/aggregate.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/aggregate.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
