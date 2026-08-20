#!/usr/bin/env bash
#SBATCH --job-name=gdp-e12-collect
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-collect-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-collect-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E12 finalizer snapshot}"
: "${TRAINING_SNAPSHOT:?missing immutable E12 training snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
RESULTS=${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b
OUTPUT=${RESULTS}/ARTIFACT-REGISTRY.json
JOB_TMP=/tmp/ckontzias-gdp-e12-collect-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
test ! -w "${TRAINING_SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${TRAINING_SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test -f "${RESULTS}/preflight/summary.json"
test -f "${RESULTS}/gpu-smoke/summary.json"
test ! -e "${OUTPUT}"
mkdir -p "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  TMPDIR="${JOB_TMP}" SLURM_JOB_ID="${SLURM_JOB_ID}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/collect_gdp_cem_e12_artifacts.py" \
  --results-root "${RESULTS}" \
  --protocol "${TRAINING_SNAPSHOT}/ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md" \
  --training-source-manifest "${TRAINING_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output "${OUTPUT}"
sha256sum "${OUTPUT}" > "${RESULTS}/ARTIFACT-REGISTRY.sha256"
