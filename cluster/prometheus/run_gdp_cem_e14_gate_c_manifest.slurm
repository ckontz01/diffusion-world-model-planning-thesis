#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-gate-c-manifest
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-c-manifest-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-c-manifest-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 Gate-C source snapshot}"
: "${GATE_B_AUDIT:?missing E14 Gate-B authorization}"
: "${GATE_B_AUDIT_SHA256:?missing E14 Gate-B audit hash}"
: "${NORMALIZED_ROOT:?missing normalized E14 training root}"
: "${NORMALIZATION_AUDIT:?missing E14 normalization audit}"
: "${NORMALIZATION_AUDIT_SHA256:?missing E14 normalization audit hash}"
: "${MANIFEST_ROOT:?missing unique E14 Gate-C manifest root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${MANIFEST_ROOT}"
mkdir -p "${MANIFEST_ROOT}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_gdp_cem_e14_gate_c_manifest.py" \
  --gate-b-audit "${GATE_B_AUDIT}" \
  --gate-b-audit-sha256 "${GATE_B_AUDIT_SHA256}" \
  --normalized-root "${NORMALIZED_ROOT}" \
  --normalization-audit "${NORMALIZATION_AUDIT}" \
  --normalization-audit-sha256 "${NORMALIZATION_AUDIT_SHA256}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-tsv "${MANIFEST_ROOT}/evaluation.tsv" \
  --output-json "${MANIFEST_ROOT}/manifest.json"
sha256sum "${MANIFEST_ROOT}/evaluation.tsv" "${MANIFEST_ROOT}/manifest.json" > "${MANIFEST_ROOT}/sha256.txt"
chmod a-w "${MANIFEST_ROOT}"/* "${MANIFEST_ROOT}"
