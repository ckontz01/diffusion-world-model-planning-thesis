#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-pathfix
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-pathfix-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-pathfix-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 Gate-C source snapshot}"
: "${MODE:?missing E14 normalization mode}"
: "${TRAINING_ROOT:?missing E14 physical training root}"
: "${ENDPOINT_MANIFEST:?missing original endpoint manifest}"
: "${ENDPOINT_MANIFEST_SHA256:?missing original endpoint manifest hash}"
: "${NORMALIZED_ROOT:?missing unique E14 normalized logical root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${NORMALIZED_ROOT}"
extra=()
case "${MODE}" in
  endpoint) ;;
  full)
    : "${SAGE_MANIFEST:?missing original SAGE manifest}"
    : "${SAGE_MANIFEST_SHA256:?missing original SAGE manifest hash}"
    extra=(--sage-manifest "${SAGE_MANIFEST}" --sage-manifest-sha256 "${SAGE_MANIFEST_SHA256}")
    ;;
  *) exit 2 ;;
esac
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/normalize_gdp_cem_e14_training_paths.py" \
  --mode "${MODE}" \
  --training-root "${TRAINING_ROOT}" \
  --endpoint-manifest "${ENDPOINT_MANIFEST}" \
  --endpoint-manifest-sha256 "${ENDPOINT_MANIFEST_SHA256}" \
  "${extra[@]}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-root "${NORMALIZED_ROOT}"
files=("${NORMALIZED_ROOT}/NORMALIZATION.json" "${NORMALIZED_ROOT}/manifests/endpoint.tsv")
if [[ "${MODE}" = full ]]; then
  files+=("${NORMALIZED_ROOT}/manifests/sage.tsv")
fi
sha256sum "${files[@]}" > "${NORMALIZED_ROOT}/sha256.txt"
find "${NORMALIZED_ROOT}" -type f -exec chmod a-w {} +
find "${NORMALIZED_ROOT}" -type d -exec chmod a-w {} +
