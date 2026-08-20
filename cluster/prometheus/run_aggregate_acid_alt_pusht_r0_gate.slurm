#!/usr/bin/env bash

# Outcome-independent R0 gate frozen before native-ACID evaluation completes.

#SBATCH --job-name=acid-alt-pusht-r0-gate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:15:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-r0-gate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-r0-gate-%j.err

set -euo pipefail

: "${B0_JOB_ID:?submit with --export=ALL,B0_JOB_ID=<B0 job>}"
: "${SCORER_JOB_ID:?submit with --export=ALL,SCORER_JOB_ID=<scorer job>}"
: "${ACID_EVAL_JOB_ID:?submit with --export=ALL,ACID_EVAL_JOB_ID=<A1 array job>}"
: "${ANALYSIS_SNAPSHOT:?submit with --export=ALL,ANALYSIS_SNAPSHOT=<immutable analysis snapshot>}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
B0="${ROOT}/results/acid-alternative/r0/pusht/b0/planner-seed-42-job-${B0_JOB_ID}/summary.json"
OUTPUT_DIR="${ROOT}/results/acid-alternative/gates/pusht/r0-b0-acid-job-${SLURM_JOB_ID}"
OUTPUT="${OUTPUT_DIR}/gate.json"
SEEDS=(6101 6102 6103)
JOB_TMP="/tmp/ckontzias-acid-alt-r0-gate-${SLURM_JOB_ID}"

test -f "${ANALYSIS_SNAPSHOT}/aggregate_acid_alt_r0_gate.py"
test -f "${ANALYSIS_SNAPSHOT}/SOURCE-MANIFEST.sha256"
test -f "${B0}"
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing existing output: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
sha256sum "$0" "${ANALYSIS_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  > "${JOB_TMP}/source-provenance.sha256"

arguments=(
  --b0-summary "${B0}"
  --minimum-b0-rate 0.86
  --expected-episodes 50
  --expected-planner-seed 42
  --output "${OUTPUT}"
)
for task in 0 1 2; do
  seed="${SEEDS[${task}]}"
  arguments+=(
    --acid-summary "${ROOT}/results/acid-alternative/r0/pusht/acid/train-seed-${seed}-planner-seed-42-job-${ACID_EVAL_JOB_ID}-${task}/summary.json"
    --acid-training-summary "${ROOT}/results/acid-alternative/scorers/pusht/acid/true/seed-${seed}-job-${SCORER_JOB_ID}-${task}/summary.json"
  )
done

# Preserve the failure report even when a scientific gate fails.
set +e
/usr/bin/python3 "${ANALYSIS_SNAPSHOT}/aggregate_acid_alt_r0_gate.py" "${arguments[@]}"
status=$?
set -e
mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT_DIR}/source-provenance.sha256"
printf '%s\n' \
  "b0_job_id=${B0_JOB_ID}" \
  "scorer_job_id=${SCORER_JOB_ID}" \
  "acid_eval_job_id=${ACID_EVAL_JOB_ID}" \
  "gate_job_id=${SLURM_JOB_ID}" \
  "gate_exit_status=${status}" \
  > "${OUTPUT_DIR}/provenance.txt"
sha256sum "${OUTPUT}" "${OUTPUT_DIR}/source-provenance.sha256" \
  "${OUTPUT_DIR}/provenance.txt" > "${OUTPUT_DIR}/sha256.txt"
exit "${status}"
