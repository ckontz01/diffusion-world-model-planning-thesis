#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-gate-b-json
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-b-json-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-b-json-%j.err

set -euo pipefail
: "${SERIALIZER_SNAPSHOT:?missing immutable E14 serializer snapshot}"
: "${OFFLINE_SNAPSHOT:?missing immutable E14 offline scientific snapshot}"
: "${ENDPOINT_MANIFEST:?missing clean E14 endpoint manifest}"
: "${ENDPOINT_MANIFEST_SHA256:?missing clean endpoint manifest hash}"
: "${FULL_EVALUATION_ROOT:?missing complete E14 full-evaluation root}"
: "${ANALYSIS_ROOT:?missing unique E14 Gate-B analysis root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
ORIGINAL_ANALYZER=${OFFLINE_SNAPSHOT}/analyze_gdp_cem_e14_offline.py
ORIGINAL_ANALYZER_SHA256=5362788ed566a5f2f876b63ff004ba878bd5278d28ed323408431f02d3572299

test ! -w "${SERIALIZER_SNAPSHOT}"
test ! -w "${OFFLINE_SNAPSHOT}"
(cd "${SERIALIZER_SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${OFFLINE_SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sha256sum "${ORIGINAL_ANALYZER}" | cut -d' ' -f1)" = \
  "${ORIGINAL_ANALYZER_SHA256}"
test "$(sha256sum "${ENDPOINT_MANIFEST}" | cut -d' ' -f1)" = \
  "${ENDPOINT_MANIFEST_SHA256}"
test ! -e "${ANALYSIS_ROOT}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${OFFLINE_SNAPSHOT}:${SERIALIZER_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  E14_ORIGINAL_ANALYZER="${ORIGINAL_ANALYZER}" \
  E14_ORIGINAL_ANALYZER_SHA256="${ORIGINAL_ANALYZER_SHA256}" \
  "${ENV_DIR}/bin/python" "${SERIALIZER_SNAPSHOT}/run_gdp_cem_e14_gate_b_serializer.py" \
  --evaluation-root "${FULL_EVALUATION_ROOT}" \
  --endpoint-manifest "${ENDPOINT_MANIFEST}" \
  --endpoint-manifest-sha256 "${ENDPOINT_MANIFEST_SHA256}" \
  --protocol "${OFFLINE_SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${OFFLINE_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${ANALYSIS_ROOT}"
printf '%s\n' \
  "serializer_source_manifest_sha256=$(sha256sum "${SERIALIZER_SNAPSHOT}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" \
  "offline_source_manifest_sha256=$(sha256sum "${OFFLINE_SNAPSHOT}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" \
  "original_analyzer_sha256=${ORIGINAL_ANALYZER_SHA256}" > "${ANALYSIS_ROOT}/SERIALIZER-PROVENANCE.txt"
(cd "${ANALYSIS_ROOT}" && sha256sum GATE-B-AUDIT.json SERIALIZER-PROVENANCE.txt > sha256.txt && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${ANALYSIS_ROOT}"/* "${ANALYSIS_ROOT}"
