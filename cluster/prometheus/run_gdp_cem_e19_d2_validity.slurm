#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-d2-validity
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-d2-validity-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-d2-validity-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E19-D2 snapshot}"
: "${RUN_ROOT:?missing unique E19-D2 run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
RAW_SNAPSHOT=${ROOT}/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0
RAW_RUN=${ROOT}/experiments/gdp-cem-e19/discrepancy-diagnostic-run-20260829-e347bc08
E19_RUN=${ROOT}/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988
OUTPUT=${RUN_ROOT}/validity
JOB_TMP=/tmp/ckontzias-gdp-e19-d2-validity-${SLURM_JOB_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
test ! -e "${OUTPUT}"
mkdir -p "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache

set +e
apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/gdp_cem_e19_d2_validity.py" \
    --d2-snapshot "${SNAPSHOT}" \
    --raw-snapshot "${RAW_SNAPSHOT}" \
    --raw-run-root "${RAW_RUN}" \
    --e19-run-root "${E19_RUN}" \
    --comparison "${RAW_RUN}/comparison/COMPARISON-AUDIT.json" \
    --output "${OUTPUT}"
status=$?
set -e
(cd "${OUTPUT}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${OUTPUT}"
exit "${status}"
