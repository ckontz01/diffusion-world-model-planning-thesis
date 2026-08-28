#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-runtime
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-runtime-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-runtime-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E19 snapshot}"
: "${RUN_ROOT:?missing unique E19 run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
SAGE=${SNAPSHOT}/official-sage
STABLEWM=${ROOT}/data/stablewm
OUTPUT=${RUN_ROOT}/runtime-preflight
JOB_TMP=/tmp/ckontzias-gdp-e19-runtime-${SLURM_JOB_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
(cd "${RUN_ROOT}/preparation" && sha256sum -c sha256.txt >/dev/null)
(cd "${RUN_ROOT}/release-audit" && sha256sum -c sha256.txt >/dev/null)
(cd "${RUN_ROOT}/data-overlap-audit" && sha256sum -c sha256.txt >/dev/null)
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
  PYTHONPATH="${SNAPSHOT}/lewm-serialization-compat:${SNAPSHOT}:${SAGE}:${SNAPSHOT}/lewm-runtime" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/audit_gdp_cem_e19_serialization_compat.py" \
    --pair "pusht=${STABLEWM}/pusht/lewm_object.ckpt,${STABLEWM}/pusht/lewm_hf_22b330c_object.ckpt" \
    --pair "cube=${STABLEWM}/cube/lewm_object.ckpt,${STABLEWM}/cube/lewm_hf_b0747c5_object.ckpt" \
    --device cuda:0 \
    --output "${OUTPUT}/RUNTIME-PREFLIGHT-AUDIT.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["all_passed"] is True' "${OUTPUT}/RUNTIME-PREFLIGHT-AUDIT.json"
(cd "${OUTPUT}" && sha256sum RUNTIME-PREFLIGHT-AUDIT.json > sha256.txt)
(cd "${OUTPUT}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${OUTPUT}"
