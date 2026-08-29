#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-compare
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=12
#SBATCH --mem=96G
#SBATCH --gres=gpu:1
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-compare-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-compare-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable discrepancy snapshot}"
: "${RUN_ROOT:?missing unique discrepancy run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
E19_RUN=/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988
OUTPUT=${RUN_ROOT}/comparison
JOB_TMP=/tmp/ckontzias-gdp-e19-compare-${SLURM_JOB_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
for sentinel in 0 1 2 3 4; do
  for repeat in 0 1; do
    (cd "${RUN_ROOT}/sentinels/s${sentinel}/r${repeat}" && sha256sum -c sha256.txt >/dev/null)
  done
done
(cd "${E19_RUN}/preparation" && sha256sum -c sha256.txt >/dev/null)
test ! -e "${OUTPUT}"
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  PYTHONPATH="${SNAPSHOT}/lewm-serialization-compat:${SNAPSHOT}:${SNAPSHOT}/official-sage:${SNAPSHOT}/lewm-runtime" \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
  TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/compare_gdp_cem_e19_discrepancy.py" \
    --snapshot "${SNAPSHOT}" \
    --run-root "${RUN_ROOT}" \
    --stablewm-root "${ROOT}/data/stablewm" \
    --flat-root "${ROOT}/downloads/acid-alternative/flat-lewm-models" \
    --pusht-hdf5 "${ROOT}/data/stablewm/pusht_expert_train.h5" \
    --pusht-lance "${E19_RUN}/preparation/pusht_expert_train.lance" \
    --device cuda:0 \
    --output "${OUTPUT}/COMPARISON-AUDIT.json"
(cd "${OUTPUT}" && sha256sum COMPARISON-AUDIT.json > sha256.txt)
(cd "${OUTPUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUTPUT}/COMPARISON-AUDIT.json" "${OUTPUT}/sha256.txt" "${OUTPUT}"
