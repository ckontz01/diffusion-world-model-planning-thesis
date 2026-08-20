#!/usr/bin/env bash
#SBATCH --job-name=gdp-e12-pre
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-pre-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-pre-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E12 Stage-B snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
OUT=${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b/preflight
JOB_TMP=/tmp/ckontzias-gdp-e12-pre-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=0 TMPDIR="${JOB_TMP}" SLURM_JOB_ID="${SLURM_JOB_ID}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/preflight_gdp_cem_e12_stage_b.py" \
  --root "${ROOT}" --snapshot "${SNAPSHOT}" \
  --prism-reference "${ROOT}/downloads/prism-jepa-baa0eb95" \
  --output "${OUT}/summary.json"
sha256sum "${OUT}/summary.json" > "${OUT}/sha256.txt"
