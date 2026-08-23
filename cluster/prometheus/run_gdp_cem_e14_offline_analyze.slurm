#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-gate-b
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-b-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-b-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 offline snapshot}"
: "${ENDPOINT_MANIFEST:?missing frozen E14 endpoint manifest}"
: "${ENDPOINT_MANIFEST_SHA256:?missing frozen E14 endpoint manifest hash}"
: "${FULL_EVALUATION_ROOT:?missing complete E14 full-evaluation root}"
: "${ANALYSIS_ROOT:?missing unique E14 Gate-B analysis root}"
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
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e14_offline.py" \
  --evaluation-root "${FULL_EVALUATION_ROOT}" \
  --endpoint-manifest "${ENDPOINT_MANIFEST}" \
  --endpoint-manifest-sha256 "${ENDPOINT_MANIFEST_SHA256}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${ANALYSIS_ROOT}"
sha256sum "${ANALYSIS_ROOT}/GATE-B-AUDIT.json" > "${ANALYSIS_ROOT}/sha256.txt"
chmod a-w "${ANALYSIS_ROOT}"/* "${ANALYSIS_ROOT}"

