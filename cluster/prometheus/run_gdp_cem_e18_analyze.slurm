#!/usr/bin/env bash
#SBATCH --job-name=gdp-e18-analyze
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e18-analyze-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e18-analyze-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E18 snapshot}"
: "${INPUT_AUDIT_ROOT:?missing passed E18 input-audit root}"
: "${P2_ROOT:?missing complete E18 P2 root}"
: "${EVALUATION_ROOT:?missing complete E18 evaluation root}"
: "${OUTPUT_ROOT:?missing unique E18 analysis root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${INPUT_AUDIT_ROOT}" && sha256sum -c sha256.txt >/dev/null)
(cd "${P2_ROOT}/pusht" && sha256sum -c sha256.txt >/dev/null)
(cd "${P2_ROOT}/cube" && sha256sum -c sha256.txt >/dev/null)
INPUT_AUDIT=${INPUT_AUDIT_ROOT}/INPUT-AUDIT.json
INPUT_AUDIT_SHA256=$(sha256sum "${INPUT_AUDIT}" | cut -d' ' -f1)
CELL_MANIFEST=${SNAPSHOT}/E18-CELLS.tsv
CELL_MANIFEST_SHA256=$(sha256sum "${CELL_MANIFEST}" | cut -d' ' -f1)
test ! -e "${OUTPUT_ROOT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e18.py" \
  --evaluation-root "${EVALUATION_ROOT}" \
  --cell-manifest "${CELL_MANIFEST}" \
  --cell-manifest-sha256 "${CELL_MANIFEST_SHA256}" \
  --input-audit "${INPUT_AUDIT}" --input-audit-sha256 "${INPUT_AUDIT_SHA256}" \
  --p2-root "${P2_ROOT}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUTPUT_ROOT}"
(cd "${OUTPUT_ROOT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUTPUT_ROOT}"/* "${OUTPUT_ROOT}"
