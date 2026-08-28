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
STAGED_CHECKPOINTS=${ROOT}/downloads/gdp-cem-e19/checkpoints-1b5afbc8eeb1c8e99d9529099e1aa15f392a6346
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
test ! -w "${STAGED_CHECKPOINTS}"
(cd "${STAGED_CHECKPOINTS}" && sha256sum -c sha256.txt >/dev/null)
for checkpoint in \
  pusht_generator.pt pusht_action_prior.pt pusht_far_action_prior.pt \
  cube_generator.pt cube_action_prior.pt cube_far_action_prior.pt; do
  cp -- "${STAGED_CHECKPOINTS}/${checkpoint}" "${CHECKPOINTS}/${checkpoint}"
done
cd "${SNAPSHOT}"
"${ENV_DIR}/bin/python" "${SNAPSHOT}/prepare_gdp_cem_e19_inputs.py" \
  --sage-root "${SAGE}" \
  --pusht-hdf5 "${ROOT}/data/stablewm/pusht_expert_train.h5" \
  --checkpoint-root "${CHECKPOINTS}" \
  --output-root "${PREPARATION}"
(cd "${PREPARATION}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${CHECKPOINTS}" "${PREPARATION}"
