#!/usr/bin/env bash
#SBATCH --job-name=gdp-post-e14-boundary
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --array=0-5%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-post-e14-boundary-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-post-e14-boundary-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable diagnostic source snapshot}"
: "${TRAINING_ROOT:?missing normalized E14 training root}"
: "${ORIGINAL_EVAL_ROOT:?missing frozen E14 full-evaluation root}"
: "${OUTPUT_ROOT:?missing unique post-E14 diagnostic output root}"
: "${MODE:?missing diagnostic mode}"
case "${MODE}" in smoke|full) ;; *) exit 2 ;; esac
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM=${ROOT}/data/stablewm

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
case "${SLURM_ARRAY_TASK_ID}" in
  0|1|2)
    TASK=pusht; SEED=$((6101 + SLURM_ARRAY_TASK_ID))
    ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; TRANSITION_JOB=296629; CACHE_JOB=298993-0
    POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt
    LEGAL_SOURCE=${ENV_DIR}/lib/python3.11/site-packages/stable_worldmodel/envs/pusht/env.py
    ;;
  3|4|5)
    TASK=cube; SEED=$((6098 + SLURM_ARRAY_TASK_ID))
    ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; TRANSITION_JOB=296667; CACHE_JOB=298993-1
    POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt
    LEGAL_SOURCE=${ENV_DIR}/lib/python3.11/site-packages/ogbench/manipspace/envs/manipspace_env.py
    ;;
  *) exit 2 ;;
esac
BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
TRANSITION=${BASE}/transition-cache-job-${TRANSITION_JOB}
CACHE=${BASE}/e14-variable-cache-job-${CACHE_JOB}
TRAINING=${TRAINING_ROOT}/endpoint/${TASK}/vad_true/seed-${SEED}
ORIGINAL=${ORIGINAL_EVAL_ROOT}/${TASK}/vad_true/seed-${SEED}
OUT=${OUTPUT_ROOT}/${TASK}/seed-${SEED}
JOB_TMP=/tmp/ckontzias-post-e14-boundary-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}

(cd "${TRAINING}" && sha256sum -c sha256.txt >/dev/null)
(cd "${ORIGINAL}" && sha256sum -c sha256.txt >/dev/null)
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
  TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/diagnose_gdp_cem_e14_boundaries.py" \
  --mode "${MODE}" --task "${TASK}" --seed "${SEED}" \
  --training-summary "${TRAINING}/summary.json" \
  --original-summary "${ORIGINAL}/summary.json" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --transition-h5 "${TRANSITION}/transitions.h5" \
  --cache-h5 "${CACHE}/cache.h5" --cache-manifest "${CACHE}/manifest.json" \
  --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM}/${CHECKPOINT}" \
  --stablewm-home "${STABLEWM}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --legal-bound-source "${LEGAL_SOURCE}" --output-dir "${OUT}"
/usr/bin/python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["descriptive_only"] is True and x["d5_read"] is False' "${OUT}/summary.json"
(cd "${OUT}" && sha256sum row-metrics.h5 summary.json > sha256.txt && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
