#!/usr/bin/env bash
#SBATCH --job-name=gdp-e15-data
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-data-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-data-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E15 data-preflight snapshot}"
: "${OUTPUT_ROOT:?missing unique E15 data-preflight output root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
STABLEWM=${ROOT}/data/stablewm

case "${SLURM_ARRAY_TASK_ID}" in
  0)
    TASK=pusht
    DATASET=${STABLEWM}/pusht_expert_train.h5
    ARTIFACT=lewm-hf-22b330c
    LATENT_JOB=296628
    TRANSITION_JOB=296629
    E14_CACHE_JOB=298993-0
    ;;
  1)
    TASK=cube
    DATASET=${STABLEWM}/cube_single_expert.h5
    ARTIFACT=lewm-hf-b0747c5
    LATENT_JOB=296666
    TRANSITION_JOB=296667
    E14_CACHE_JOB=298993-1
    ;;
  *) exit 2 ;;
esac

BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
TRANSITION=${BASE}/transition-cache-job-${TRANSITION_JOB}
E14_CACHE=${BASE}/e14-variable-cache-job-${E14_CACHE_JOB}
OUT=${OUTPUT_ROOT}/${TASK}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/build_gdp_cem_e15_bounded_cache.py" \
  --task "${TASK}" --dataset "${DATASET}" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --transition-h5 "${TRANSITION}/transitions.h5" \
  --e14-cache-h5 "${E14_CACHE}/cache.h5" \
  --e14-cache-manifest "${E14_CACHE}/manifest.json" \
  --preflight-spec "${SNAPSHOT}/E15-BOUNDARY-AWARE-DATA-PREFLIGHT-SPEC-2026-08-25.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-h5 "${OUT}/cache.h5" --output-json "${OUT}/manifest.json"

/usr/bin/python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["model_training_performed"] is False and x["d5_read"] is False' "${OUT}/manifest.json"
sha256sum "${OUT}/cache.h5" "${OUT}/manifest.json" > "${OUT}/sha256.txt"
(cd "${OUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
