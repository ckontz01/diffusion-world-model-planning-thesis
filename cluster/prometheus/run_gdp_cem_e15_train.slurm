#!/usr/bin/env bash
#SBATCH --job-name=gdp-e15-train
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=12:00:00
#SBATCH --array=0-21%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-train-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-train-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E15 training snapshot}"
: "${DATA_ROOT:?missing immutable E15 data root}"
: "${PREFLIGHT_ROOT:?missing completed E15 training-preflight root}"
: "${OUTPUT_ROOT:?missing unique E15 training output root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STABLEWM=${ROOT}/data/stablewm
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006

TASK_INDEX=$((SLURM_ARRAY_TASK_ID / 11))
LOCAL_INDEX=$((SLURM_ARRAY_TASK_ID % 11))
case "${TASK_INDEX}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628 ;;
  1) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666 ;;
  *) exit 2 ;;
esac
case "${LOCAL_INDEX}" in
  0|1|2) CONDITION=vad; SEED=$((7201 + LOCAL_INDEX)) ;;
  3|4|5) CONDITION=diagonal_gaussian; SEED=$((7198 + LOCAL_INDEX)) ;;
  6|7|8) CONDITION=direct_gmm; SEED=$((7195 + LOCAL_INDEX)) ;;
  9) CONDITION=vad_shuffled; SEED=7201 ;;
  10) CONDITION=vad_unconditional; SEED=7201 ;;
  *) exit 2 ;;
esac

BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
OUT=${OUTPUT_ROOT}/${TASK}/${CONDITION}/seed-${SEED}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test -f "${PREFLIGHT_ROOT}/${TASK}.json"
test -f "${PREFLIGHT_ROOT}/${TASK}.json.sha256"
(cd "${PREFLIGHT_ROOT}" && sha256sum -c "${TASK}.json.sha256" >/dev/null)
/usr/bin/python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["validation_payload_rows_read"]==0 and x["d5_read"] is False' "${PREFLIGHT_ROOT}/${TASK}.json"
test ! -e "${OUT}"
mkdir -p "${OUT}"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/train_gdp_cem_e15_proposer.py" \
  --task "${TASK}" --condition "${CONDITION}" --seed "${SEED}" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --cache-h5 "${DATA_ROOT}/${TASK}/cache.h5" \
  --cache-manifest "${DATA_ROOT}/${TASK}/manifest.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUT}"

/usr/bin/python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["validation_payload_rows_read"]==0 and x["d5_read"] is False' "${OUT}/summary.json"
(cd "${OUT}" && sha256sum final.pt training.jsonl summary.json > sha256.txt && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
