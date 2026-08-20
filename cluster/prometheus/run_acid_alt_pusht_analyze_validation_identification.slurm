#!/usr/bin/env bash

# Paired episode-cluster analysis of D1 held-out action identification.

#SBATCH --job-name=acid-alt-pusht-val-id
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-val-id-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-val-id-%j.err

set -euo pipefail
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${CORE_SCORER_JOB_ID:?submit with core scorer array job ID}"
: "${CONTROL_JOB_ID:?submit with transition-control array job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
CORE_SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
OUTPUT="${ROOT}/results/acid-alternative/diagnostics/pusht/d1-validation-identification/job-${SLURM_JOB_ID}"

test -f "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"
test -f "${SOURCE_MANIFEST}"
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}"

runs=()
seeds=(6101 6102 6103)
for index in 0 1 2; do
  seed="${seeds[${index}]}"
  runs+=(--run "pusht=${ROOT}/results/acid-alternative/scorers/pusht/diffusion/true/seed-${seed}-job-${CORE_SCORER_JOB_ID}-$((3 + index))/summary.json")
  runs+=(--run "pusht=${ROOT}/results/acid-alternative/scorers/pusht/forward/true/seed-${seed}-job-${CORE_SCORER_JOB_ID}-$((6 + index))/summary.json")
  runs+=(--run "pusht=${ROOT}/results/acid-alternative/scorers/pusht/diffusion/shuffled_action/seed-${seed}-job-${CONTROL_JOB_ID}-${index}/summary.json")
done
for ((index = 1; index < ${#runs[@]}; index += 2)); do
  declaration="${runs[${index}]}"
  test -f "${declaration#*=}"
done

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  "${IMAGE}" env \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}" \
  "${ENV_DIR}/bin/python" -m acid_alternative_diagnostics.analyze_validation_identification \
    --analysis-role D1 \
    --source-manifest "${SOURCE_MANIFEST}" \
    --bootstrap-seed 2026081304 \
    --bootstrap-repetitions 100000 \
    --output-dir "${OUTPUT}" \
    "${runs[@]}"

sha256sum "$0" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${SOURCE_MANIFEST}" \
  "${OUTPUT}/summary.json" "${OUTPUT}/episode-identification.tsv" \
  > "${OUTPUT}/sha256.txt"
