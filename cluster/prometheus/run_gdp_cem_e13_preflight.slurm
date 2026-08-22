#!/usr/bin/env bash
#SBATCH --job-name=gdp-e13-preflight
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-preflight-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-preflight-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E13 snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
OUT=${ROOT}/results/acid-alternative/gdp-cem-e13/preflight/job-${SLURM_JOB_ID}
SMOKE_MANIFESTS=${OUT}/p1-smoke-manifests
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
test ! -e "${ROOT}/manifests/gdp-cem-e13-d4"
test ! -e "${ROOT}/results/acid-alternative/gdp-cem-e13-d4"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  SLURM_JOB_ID="${SLURM_JOB_ID}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/preflight_gdp_cem_e13.py" \
  --root "${ROOT}" --snapshot "${SNAPSHOT}" \
  --e12-stage-b-audit "${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b/STAGE-B-AUDIT.json" \
  --e12-training-source-manifest "${ROOT}/snapshots/gdp-cem-e12-stage-b-e2faf062f3eec188/SOURCE-MANIFEST.sha256" \
  --smoke-manifest-root "${SMOKE_MANIFESTS}" --output "${OUT}/summary.json"
python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"] == "ok" and x["d4_read"] is False' "${OUT}/summary.json"
find "${SMOKE_MANIFESTS}" -type f -exec chmod a-w {} +
sha256sum "${OUT}/summary.json" > "${OUT}/sha256.txt"
find "${SMOKE_MANIFESTS}" -type d -exec chmod a-w {} +
chmod a-w "${OUT}/summary.json" "${OUT}/sha256.txt" "${SMOKE_MANIFESTS}" "${OUT}"
