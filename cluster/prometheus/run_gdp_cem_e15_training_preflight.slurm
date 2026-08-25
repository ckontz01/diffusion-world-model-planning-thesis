#!/usr/bin/env bash
#SBATCH --job-name=gdp-e15-train-pre
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-train-pre-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-train-pre-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E15 training snapshot}"
: "${DATA_ROOT:?missing immutable E15 data root}"
: "${OUTPUT_ROOT:?missing unique E15 training-preflight output root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STABLEWM=${ROOT}/data/stablewm
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006

case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628 ;;
  1) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666 ;;
  *) exit 2 ;;
esac
BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
OUT=${OUTPUT_ROOT}/${TASK}.json

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test -r "${DATA_ROOT}/${TASK}/cache.h5"
test ! -e "${OUT}"
mkdir -p "${OUTPUT_ROOT}"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/preflight_gdp_cem_e15_training.py" \
  --task "${TASK}" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --cache-h5 "${DATA_ROOT}/${TASK}/cache.h5" \
  --cache-manifest "${DATA_ROOT}/${TASK}/manifest.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-json "${OUT}"
sha256sum "${OUT}" > "${OUT}.sha256"
chmod a-w "${OUT}" "${OUT}.sha256"
