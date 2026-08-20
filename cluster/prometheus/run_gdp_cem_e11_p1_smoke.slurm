#!/usr/bin/env bash
#SBATCH --job-name=gdp-e11-p1-smoke
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e11-p1-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e11-p1-smoke-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E11 snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
OUT=${ROOT}/results/acid-alternative/gdp-cem-e11-p1-smoke/job-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
test ! -e "${ROOT}/manifests/gdp-cem-e11-d3"
mkdir -p "${OUT}"
JOB_TMP=/tmp/ckontzias-gdp-e11-p1-smoke-${SLURM_JOB_ID}
mkdir -p "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
  SDL_VIDEODRIVER=dummy MPLBACKEND=Agg SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/smoke_gdp_cem_e11_p1.py" \
  --root "${ROOT}" --code-root "${CODE}" --stablewm-home "${ROOT}/data/stablewm" \
  --dataset "${ROOT}/data/stablewm/pusht_expert_train.h5" \
  --world-model-checkpoint "${ROOT}/data/stablewm/pusht/lewm_hf_22b330c_object.ckpt" \
  --proposal-summary "${ROOT}/results/acid-alternative/gdp-cem-e10v-train/pusht/vp_true/seed-6101-job-297778-0/summary.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e11_p1_smoke" "job_id=${SLURM_JOB_ID}" \
  "d3_read=false" "protected_c1_i1_read=false" > "${OUT}/audit.txt"
sha256sum "${OUT}/summary.json" "${OUT}/audit.txt" > "${OUT}/sha256.txt"
