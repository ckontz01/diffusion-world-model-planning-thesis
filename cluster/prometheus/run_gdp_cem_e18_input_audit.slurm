#!/usr/bin/env bash
#SBATCH --job-name=gdp-e18-inputs
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e18-inputs-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e18-inputs-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E18 snapshot}"
: "${E15_TRAINING_ROOT:?missing immutable E15 training root}"
: "${E17_RUN_ROOT:?missing immutable E17 run root}"
: "${OUTPUT_ROOT:?missing unique E18 input-audit root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUTPUT_ROOT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/validate_gdp_cem_e18_inputs.py" \
  --e15-training-root "${E15_TRAINING_ROOT}" \
  --e17-model-root "${E17_RUN_ROOT}/models" \
  --e17-audit "${E17_RUN_ROOT}/analysis/ADAPTER-PREFLIGHT-AUDIT.json" \
  --e17-task-first "${E17_RUN_ROOT}/analysis/task-first.tsv" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUTPUT_ROOT}"
(cd "${OUTPUT_ROOT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUTPUT_ROOT}"/* "${OUTPUT_ROOT}"
