#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-prepare
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-prepare-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-prepare-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E19 snapshot}"
: "${RUN_ROOT:?missing unique E19 run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
SAGE=${SNAPSHOT}/official-sage
CHECKPOINTS=${RUN_ROOT}/checkpoints
PREPARATION=${RUN_ROOT}/preparation
JOB_TMP=/tmp/ckontzias-gdp-e19-prepare-${SLURM_JOB_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
test ! -e "${CHECKPOINTS}"
test ! -e "${PREPARATION}"
mkdir -p "${CHECKPOINTS}" "${JOB_TMP}"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export TMPDIR=${JOB_TMP} PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export PYTHONPATH=${SAGE}:${SNAPSHOT}
export HF_HOME=${RUN_ROOT}/hf-cache HF_HUB_DISABLE_TELEMETRY=1

cd "${SAGE}"
"${ENV_DIR}/bin/python" scripts/download_checkpoints.py \
  --repo-id CLTRAY/SAGE \
  --revision 1b5afbc8eeb1c8e99d9529099e1aa15f392a6346 \
  --out-dir "${CHECKPOINTS}" \
  --registry "${SAGE}/configs/checkpoints.json"
cd "${SNAPSHOT}"
"${ENV_DIR}/bin/python" "${SNAPSHOT}/prepare_gdp_cem_e19_inputs.py" \
  --sage-root "${SAGE}" \
  --pusht-hdf5 "${ROOT}/data/stablewm/pusht_expert_train.h5" \
  --checkpoint-root "${CHECKPOINTS}" \
  --output-root "${PREPARATION}"
(cd "${PREPARATION}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${CHECKPOINTS}" "${PREPARATION}"
