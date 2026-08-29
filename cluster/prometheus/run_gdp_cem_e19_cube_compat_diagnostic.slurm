#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-cube-compat
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-cube-compat-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-cube-compat-%j.err

set -euo pipefail
: "${STAGED_ROOT:?missing staged E19 wrappers}"
: "${SAGE_ROOT:?missing pinned official SAGE checkout}"
: "${LEWM_RUNTIME:?missing pinned historical LeWM runtime}"
: "${CHECKPOINT_ROOT:?missing exact E19 checkpoint directory}"
: "${OUTPUT:?missing unique diagnostic output}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
JOB_TMP=/tmp/ckontzias-gdp-e19-cube-compat-${SLURM_JOB_ID}

test ! -e "${OUTPUT}"
test "$(git -C "${SAGE_ROOT}" rev-parse HEAD)" = 8219029fd52e89157e05aebb998ab26f0ef46966
test -z "$(git -C "${SAGE_ROOT}" status --porcelain --untracked-files=all)"
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
  PYTHONPATH="${STAGED_ROOT}/e19_lewm_serialization_compat:${STAGED_ROOT}:${SAGE_ROOT}:${LEWM_RUNTIME}" \
  "${ENV_DIR}/bin/python" "${STAGED_ROOT}/audit_gdp_cem_e19_cube_generator_compat.py" \
    --lewm "${ROOT}/data/stablewm/cube/lewm_hf_b0747c5_object.ckpt" \
    --generator "${CHECKPOINT_ROOT}/cube_generator.pt" \
    --action-prior "${CHECKPOINT_ROOT}/cube_action_prior.pt" \
    --device cuda:0 \
    --output "${OUTPUT}/CUBE-GENERATOR-COMPAT-AUDIT.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["all_passed"] is True' "${OUTPUT}/CUBE-GENERATOR-COMPAT-AUDIT.json"
(cd "${OUTPUT}" && sha256sum CUBE-GENERATOR-COMPAT-AUDIT.json > sha256.txt)
(cd "${OUTPUT}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${OUTPUT}"
