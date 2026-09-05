#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-l1
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-l1-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-l1-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing L1 snapshot}"
: "${RUN_ROOT:?missing fresh L1 run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
PARENT=${ROOT}/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0
E19_RUN=${ROOT}/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
JOB_TMP=${RUN_ROOT}/tmp-${SLURM_JOB_ID}
case "${SNAPSHOT}" in "${ROOT}"/snapshots/gdp-cem-e19-l1-*) ;; *) exit 2;; esac
case "${RUN_ROOT}" in "${ROOT}"/experiments/gdp-cem-e19-l1/localization-run-*) ;; *) exit 2;; esac
test ! -w "${SNAPSHOT}"
test ! -e "${RUN_ROOT}/analysis"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${PARENT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${E19_RUN}/preparation" && sha256sum -c sha256.txt >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
mkdir -p "${JOB_TMP}/apptainer"
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}:ro" --bind "${RUN_ROOT}:${RUN_ROOT}:rw" \
  "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  PYTHONPATH="${SNAPSHOT}:${PARENT}/lewm-serialization-compat:${PARENT}:${PARENT}/official-sage:${PARENT}/lewm-runtime" \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl TMPDIR="${JOB_TMP}" MPLCONFIGDIR="${JOB_TMP}/mpl" \
  "${ENV_DIR}/bin/python" -m pytest -q -p no:cacheprovider "${SNAPSHOT}/test_gdp_cem_e19_l1_tools.py"
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}:ro" --bind "${RUN_ROOT}:${RUN_ROOT}:rw" \
  "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  PYTHONPATH="${SNAPSHOT}:${PARENT}/lewm-serialization-compat:${PARENT}:${PARENT}/official-sage:${PARENT}/lewm-runtime" \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl TMPDIR="${JOB_TMP}" MPLCONFIGDIR="${JOB_TMP}/mpl" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e19_l1.py" --output "${RUN_ROOT}/analysis"
(cd "${RUN_ROOT}/analysis" && sha256sum -c sha256.txt)
