#!/usr/bin/env bash
#SBATCH --job-name=gdp-post-e14-boundary-audit
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-post-e14-boundary-audit-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-post-e14-boundary-audit-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable diagnostic snapshot}"
: "${EVALUATION_ROOT:?missing complete boundary-evaluation root}"
: "${ANALYSIS_ROOT:?missing unique boundary-analysis root}"
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
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_post_e14_boundary_diagnostic.py" \
  --evaluation-root "${EVALUATION_ROOT}" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${ANALYSIS_ROOT}"
(cd "${ANALYSIS_ROOT}" && sha256sum BOUNDARY-DIAGNOSTIC-AUDIT.json > sha256.txt && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${ANALYSIS_ROOT}"/* "${ANALYSIS_ROOT}"
