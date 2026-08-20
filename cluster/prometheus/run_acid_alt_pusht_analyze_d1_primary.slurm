#!/usr/bin/env bash

# Analyze the complete primary PushT development matrix after all 15 runs succeed.

#SBATCH --job-name=acid-alt-pusht-d1-stats
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-stats-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-stats-%j.err

set -euo pipefail
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${D1_JOB_ID:?submit with primary D1 array job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
CORE_SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
OUTPUT="${ROOT}/results/acid-alternative/d1/pusht/analysis-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-d1-stats-${SLURM_JOB_ID}"
ARMS=(b0 acid reachability diffusion forward)
SEEDS=(6101 6102 6103)
PLANNER_SEEDS=(7101 7102 7103)

run_arguments=()
for arm_index in 0 1 2 3 4; do
  arm="${ARMS[${arm_index}]}"
  for seed_index in 0 1 2; do
    task_id="$((arm_index * 3 + seed_index))"
    seed="${SEEDS[${seed_index}]}"
    planner_seed="${PLANNER_SEEDS[${seed_index}]}"
    summary="${ROOT}/results/acid-alternative/d1/pusht/${arm}/train-seed-${seed}-planner-seed-${planner_seed}-job-${D1_JOB_ID}-${task_id}/summary.json"
    test -f "${summary}"
    run_arguments+=(--run "pusht=${arm}=${seed}=${summary}")
  done
done
for required in "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${IMAGE}"; do
  test -f "${required}"
done
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
sha256sum "$0" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  > "${JOB_TMP}/source-provenance.sha256"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -s -- \
  "${DIAG_SNAPSHOT}" "${CORE_SNAPSHOT}" "${TOOLS_DIR}" "${ENV_DIR}" \
  "${OUTPUT}" "${JOB_TMP}" "${run_arguments[@]}" <<'CONTAINER'
set -euo pipefail
DIAG_SNAPSHOT="$1"; shift
CORE_SNAPSHOT="$1"; shift
TOOLS_DIR="$1"; shift
ENV_DIR="$1"; shift
OUTPUT="$1"; shift
JOB_TMP="$1"; shift
export PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}"
export TMPDIR="${JOB_TMP}"
python -m acid_alternative_diagnostics.analyze_closed_loop \
  --role development \
  --expected-starts 24 \
  --bootstrap-seed 2026081302 \
  --bootstrap-repetitions 100000 \
  --output-dir "${OUTPUT}" \
  "$@"
CONTAINER
mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
sha256sum "${OUTPUT}/summary.json" "${OUTPUT}/paired-outcomes.tsv" \
  "${OUTPUT}/source-provenance.sha256" > "${OUTPUT}/sha256.txt"
