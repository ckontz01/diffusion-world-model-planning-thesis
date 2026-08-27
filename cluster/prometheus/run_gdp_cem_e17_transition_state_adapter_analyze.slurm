#!/usr/bin/env bash
#SBATCH --job-name=gdp-e17-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e17-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e17-audit-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E17 snapshot}"
: "${CACHE_ROOT:?missing complete immutable E17 cache root}"
: "${MODEL_ROOT:?missing complete E17 adapter root}"
: "${OUTPUT_ROOT:?missing unique E17 analysis root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
SOURCE_SHA=$(sha256sum "${SNAPSHOT}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
test ! -e "${OUTPUT_ROOT}"
mkdir -p "${OUTPUT_ROOT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" \
  "${SNAPSHOT}/analyze_gdp_cem_e17_transition_state_adapter.py" \
  --cache-root "${CACHE_ROOT}" --model-root "${MODEL_ROOT}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md" \
  --source-manifest-sha256 "${SOURCE_SHA}" --output-dir "${OUTPUT_ROOT}"
(cd "${OUTPUT_ROOT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUTPUT_ROOT}"/* "${OUTPUT_ROOT}"
