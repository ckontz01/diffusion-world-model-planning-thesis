#!/usr/bin/env bash
#SBATCH --job-name=gdp-e17-cache
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=12:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e17-cache-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e17-cache-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E17 snapshot}"
: "${E15_DATA_ROOT:?missing immutable E15 P1 data root}"
: "${E16_RUN_ROOT:?missing completed E16 diagnostic root}"
: "${OUTPUT_ROOT:?missing unique E17 cache root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STABLEWM=${ROOT}/data/stablewm
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm

case "${SLURM_ARRAY_TASK_ID}" in
  0)
    TASK=pusht; DATASET=pusht_expert_train.h5
    ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628
    POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt
    ;;
  1)
    TASK=cube; DATASET=cube_single_expert.h5
    ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666
    POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt
    ;;
  *) exit 2 ;;
esac
BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
OUT=${OUTPUT_ROOT}/${TASK}
JOB_TMP=/tmp/ckontzias-gdp-e17-cache-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${E15_DATA_ROOT}/${TASK}" && sha256sum -c sha256.txt >/dev/null)
(cd "${E16_RUN_ROOT}/stage-a-analysis" && sha256sum -c sha256.txt >/dev/null)
(cd "${E16_RUN_ROOT}/adapters/${TASK}" && sha256sum -c sha256.txt >/dev/null)
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
  TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" \
  "${SNAPSHOT}/build_gdp_cem_e17_transition_state_cache.py" \
  --task "${TASK}" --dataset "${STABLEWM}/${DATASET}" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --cache-h5 "${E15_DATA_ROOT}/${TASK}/cache.h5" \
  --cache-manifest "${E15_DATA_ROOT}/${TASK}/manifest.json" \
  --world-model-policy "${POLICY}" \
  --world-model-checkpoint "${STABLEWM}/${CHECKPOINT}" \
  --stablewm-home "${STABLEWM}" \
  --e16-stage-a-audit "${E16_RUN_ROOT}/stage-a-analysis/STAGE-A-AUDIT.json" \
  --e16-task-first "${E16_RUN_ROOT}/stage-a-analysis/task-first.tsv" \
  --e16-adapter-summary "${E16_RUN_ROOT}/adapters/${TASK}/summary.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-h5 "${OUT}/cache.h5" --output-json "${OUT}/manifest.json"

/usr/bin/python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["validation_metrics_computed"] is False and x["d5_read"] is False' "${OUT}/manifest.json"
(cd "${OUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
