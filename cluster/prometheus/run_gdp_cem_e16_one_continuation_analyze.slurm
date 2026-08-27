#!/usr/bin/env bash
#SBATCH --job-name=gdp-e16-cont-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e16-cont-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e16-cont-audit-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E16 Stage-B snapshot}"
: "${INPUT_ROOT:?missing complete E16 Stage-B root}"
: "${OUTPUT_ROOT:?missing unique E16 Stage-B analysis root}"
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
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e16_one_continuation.py" \
  --input-root "${INPUT_ROOT}" --source-manifest-sha256 "${SOURCE_SHA}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E16-CONTINUATION-AWARE-DIRECT-VAD-DEVELOPMENT-PROTOCOL-2026-08-27.md" \
  --output-dir "${OUTPUT_ROOT}"
(cd "${OUTPUT_ROOT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUTPUT_ROOT}"/* "${OUTPUT_ROOT}"

