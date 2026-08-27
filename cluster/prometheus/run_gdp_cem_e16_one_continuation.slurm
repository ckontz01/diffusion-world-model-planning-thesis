#!/usr/bin/env bash
#SBATCH --job-name=gdp-e16-one-cont
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=12:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e16-one-cont-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e16-one-cont-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E16 Stage-B snapshot}"
: "${TRAINING_ROOT:?missing E15 training root}"
: "${DATA_ROOT:?missing E15 data root}"
: "${ADAPTER_ROOT:?missing complete passed E16 adapter root}"
: "${STAGE_A_ROOT:?missing complete E16 Stage-A audit root}"
: "${OUTPUT_ROOT:?missing unique E16 Stage-B root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM=${ROOT}/data/stablewm

case "${SLURM_ARRAY_TASK_ID}" in
  0)
    TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628
    POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt
    ;;
  1)
    TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666
    POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt
    ;;
  *) exit 2 ;;
esac
BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
TRAINING=${TRAINING_ROOT}/${TASK}/vad/seed-7201
OUT=${OUTPUT_ROOT}/${TASK}
JOB_TMP=/tmp/ckontzias-gdp-e16-one-cont-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${TRAINING}" && sha256sum -c sha256.txt >/dev/null)
(cd "${ADAPTER_ROOT}/${TASK}" && sha256sum -c sha256.txt >/dev/null)
(cd "${STAGE_A_ROOT}" && sha256sum -c sha256.txt >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/diagnose_gdp_cem_e16_one_continuation.py" \
  --task "${TASK}" --training-dir "${TRAINING}" \
  --adapter-dir "${ADAPTER_ROOT}/${TASK}" --stage-a-dir "${STAGE_A_ROOT}" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --cache-h5 "${DATA_ROOT}/${TASK}/cache.h5" --cache-manifest "${DATA_ROOT}/${TASK}/manifest.json" \
  --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM}/${CHECKPOINT}" \
  --stablewm-home "${STABLEWM}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E16-CONTINUATION-AWARE-DIRECT-VAD-DEVELOPMENT-PROTOCOL-2026-08-27.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
(cd "${OUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"

