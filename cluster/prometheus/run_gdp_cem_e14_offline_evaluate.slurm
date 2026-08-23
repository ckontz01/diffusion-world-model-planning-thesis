#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-offline
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --array=0-31%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-offline-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-offline-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 offline snapshot}"
: "${TRAINING_RUN_ROOT:?missing completed E14 training root}"
: "${ENDPOINT_MANIFEST:?missing frozen E14 endpoint manifest}"
: "${ENDPOINT_MANIFEST_SHA256:?missing frozen E14 endpoint manifest hash}"
: "${EVALUATION_ROOT:?missing unique E14 evaluation root}"
: "${MODE:?missing E14 evaluation mode}"
case "${MODE}" in smoke|full) ;; *) exit 2 ;; esac
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM=${ROOT}/data/stablewm

test "$(sha256sum "${ENDPOINT_MANIFEST}" | cut -d' ' -f1)" = "${ENDPOINT_MANIFEST_SHA256}"
record=$(awk -F '\t' -v id="${SLURM_ARRAY_TASK_ID}" 'NR>1 && $1==id {print $0}' "${ENDPOINT_MANIFEST}")
test -n "${record}"
IFS=$'\t' read -r ARRAY_ID TASK CONDITION SEED <<< "${record}"
test "${ARRAY_ID}" = "${SLURM_ARRAY_TASK_ID}"

case "${TASK}" in
  pusht)
    ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; CACHE_JOB=298993-0
    POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt
    ;;
  cube)
    ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; CACHE_JOB=298993-1
    POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt
    ;;
  *) exit 2 ;;
esac
BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
CACHE=${BASE}/e14-variable-cache-job-${CACHE_JOB}
TRAINING=${TRAINING_RUN_ROOT}/endpoint/${TASK}/${CONDITION}/seed-${SEED}
OUT=${EVALUATION_ROOT}/${TASK}/${CONDITION}/seed-${SEED}
JOB_TMP=/tmp/ckontzias-gdp-e14-offline-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${TRAINING}" && sha256sum -c sha256.txt >/dev/null)
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
  TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e14_offline.py" \
  --mode "${MODE}" --task "${TASK}" --condition "${CONDITION}" --seed "${SEED}" \
  --training-summary "${TRAINING}/summary.json" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --cache-h5 "${CACHE}/cache.h5" --cache-manifest "${CACHE}/manifest.json" \
  --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM}/${CHECKPOINT}" \
  --stablewm-home "${STABLEWM}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
"${ENV_DIR}/bin/python" -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["mode"]==sys.argv[2] and x["claim_allowed"] is False' "${OUT}/summary.json" "${MODE}"
(cd "${OUT}" && sha256sum metrics.h5 summary.json > sha256.txt && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"

