#!/usr/bin/env bash
#SBATCH --job-name=gdp-e12-smoke
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-smoke-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E12 Stage-B snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
OUT=${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b/gpu-smoke
JOB_TMP=/tmp/ckontzias-gdp-e12-smoke-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 HDF5_USE_FILE_LOCKING=FALSE \
  TMPDIR="${JOB_TMP}" SLURM_JOB_ID="${SLURM_JOB_ID}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/smoke_gdp_cem_e12_prism_dp_gpu.py" \
  --root "${ROOT}" --snapshot "${SNAPSHOT}" --output "${OUT}/summary.json"
sha256sum "${OUT}/summary.json" > "${OUT}/sha256.txt"
