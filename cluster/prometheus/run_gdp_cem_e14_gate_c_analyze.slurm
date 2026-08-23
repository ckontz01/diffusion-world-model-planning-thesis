#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-gate-c-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-c-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-c-audit-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 Gate-C source snapshot}"
: "${GATE_C_MANIFEST:?missing frozen E14 Gate-C manifest}"
: "${GATE_C_MANIFEST_SHA256:?missing E14 Gate-C manifest hash}"
: "${GATE_C_PROVENANCE:?missing E14 Gate-C manifest provenance}"
: "${GATE_C_PROVENANCE_SHA256:?missing E14 Gate-C provenance hash}"
: "${NORMALIZED_ROOT:?missing normalized E14 training root}"
: "${NORMALIZATION_AUDIT:?missing E14 normalization audit}"
: "${NORMALIZATION_AUDIT_SHA256:?missing E14 normalization audit hash}"
: "${GATE_B_AUDIT:?missing E14 Gate-B authorization}"
: "${GATE_B_AUDIT_SHA256:?missing E14 Gate-B audit hash}"
: "${EVALUATION_ROOT:?missing complete E14 Gate-C evaluation root}"
: "${ANALYSIS_ROOT:?missing unique E14 Gate-C analysis root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${ANALYSIS_ROOT}"
mkdir -p "${ANALYSIS_ROOT}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e14_gate_c.py" \
  --evaluation-root "${EVALUATION_ROOT}" \
  --gate-c-manifest "${GATE_C_MANIFEST}" \
  --gate-c-manifest-sha256 "${GATE_C_MANIFEST_SHA256}" \
  --gate-c-provenance "${GATE_C_PROVENANCE}" \
  --gate-c-provenance-sha256 "${GATE_C_PROVENANCE_SHA256}" \
  --normalized-root "${NORMALIZED_ROOT}" \
  --normalization-audit "${NORMALIZATION_AUDIT}" \
  --normalization-audit-sha256 "${NORMALIZATION_AUDIT_SHA256}" \
  --gate-b-audit "${GATE_B_AUDIT}" \
  --gate-b-audit-sha256 "${GATE_B_AUDIT_SHA256}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --implementation-decisions "${SNAPSHOT}/ACID-ALTERNATIVE-E14-IMPLEMENTATION-DECISIONS-1-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${ANALYSIS_ROOT}"
sha256sum "${ANALYSIS_ROOT}/GATE-C-AUDIT.json" > "${ANALYSIS_ROOT}/sha256.txt"
chmod a-w "${ANALYSIS_ROOT}"/* "${ANALYSIS_ROOT}"
