#!/usr/bin/env bash
#SBATCH --job-name=gdp-e15-gate-c-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-gate-c-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-gate-c-audit-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E15 Gate-C snapshot}"
: "${EVALUATION_ROOT:?missing complete E15 Gate-C evaluation root}"
: "${GATE_A_AUDIT:?missing passed E15 Gate-A audit}"
: "${GATE_A_AUDIT_SHA256:?missing E15 Gate-A audit hash}"
: "${GATE_B_AUDIT:?missing passed E15 Gate-B audit}"
: "${GATE_B_AUDIT_SHA256:?missing E15 Gate-B audit hash}"
: "${ANALYSIS_ROOT:?missing unique E15 Gate-C analysis root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${ANALYSIS_ROOT}"
mkdir -p "${ANALYSIS_ROOT}"
CELL_MANIFEST=${SNAPSHOT}/E15-GATE-C-CELLS.tsv
CELL_MANIFEST_SHA256=$(sha256sum "${CELL_MANIFEST}" | cut -d' ' -f1)
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e15_gate_c.py" \
  --evaluation-root "${EVALUATION_ROOT}" \
  --cell-manifest "${CELL_MANIFEST}" --cell-manifest-sha256 "${CELL_MANIFEST_SHA256}" \
  --gate-a-audit "${GATE_A_AUDIT}" \
  --gate-a-audit-sha256 "${GATE_A_AUDIT_SHA256}" \
  --gate-b-audit "${GATE_B_AUDIT}" \
  --gate-b-audit-sha256 "${GATE_B_AUDIT_SHA256}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${ANALYSIS_ROOT}"
(cd "${ANALYSIS_ROOT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${ANALYSIS_ROOT}"/* "${ANALYSIS_ROOT}"
