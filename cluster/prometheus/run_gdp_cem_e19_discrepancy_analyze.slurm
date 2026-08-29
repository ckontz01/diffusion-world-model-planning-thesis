#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-diag-analyze
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-diag-analyze-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-diag-analyze-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable discrepancy snapshot}"
: "${RUN_ROOT:?missing unique discrepancy run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
E19_RUN=/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988
OUTPUT=${RUN_ROOT}/analysis
JOB_TMP=/tmp/ckontzias-gdp-e19-diag-analyze-${SLURM_JOB_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
for sentinel in 0 1 2 3 4; do
  for repeat in 0 1; do
    (cd "${RUN_ROOT}/sentinels/s${sentinel}/r${repeat}" && sha256sum -c sha256.txt >/dev/null)
  done
done
(cd "${RUN_ROOT}/comparison" && sha256sum -c sha256.txt >/dev/null)
(cd "${E19_RUN}/analysis" && sha256sum -c sha256.txt >/dev/null)
test ! -e "${OUTPUT}"
mkdir -p "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPATH="${SNAPSHOT}:${SNAPSHOT}/official-sage:${SNAPSHOT}/lewm-runtime" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e19_discrepancy.py" \
    --snapshot "${SNAPSHOT}" \
    --run-root "${RUN_ROOT}" \
    --e19-run-root "${E19_RUN}" \
    --comparison "${RUN_ROOT}/comparison/COMPARISON-AUDIT.json" \
    --output "${OUTPUT}"
(cd "${OUTPUT}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${OUTPUT}"
