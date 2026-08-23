#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-preflight
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-preflight-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-preflight-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 training snapshot}"
: "${PREFLIGHT_ROOT:?missing unique E14 preflight output root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STABLEWM=${ROOT}/data/stablewm
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006

case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; CACHE_JOB=298993-0 ;;
  1) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; CACHE_JOB=298993-1 ;;
  *) exit 2 ;;
esac
BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
CACHE=${BASE}/e14-variable-cache-job-${CACHE_JOB}
OUT=${PREFLIGHT_ROOT}/${TASK}.json

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${PREFLIGHT_ROOT}"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/preflight_gdp_cem_e14_training.py" \
  --task "${TASK}" \
  --latent-h5 "${LATENT}/latents.h5" \
  --latent-manifest "${LATENT}/manifest.json" \
  --cache-h5 "${CACHE}/cache.h5" \
  --cache-manifest "${CACHE}/manifest.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-json "${OUT}"
sha256sum "${OUT}" > "${OUT}.sha256"
