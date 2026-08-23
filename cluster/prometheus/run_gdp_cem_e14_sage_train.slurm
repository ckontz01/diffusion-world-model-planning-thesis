#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-sage
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --array=0-5%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-sage-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-sage-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 training snapshot}"
: "${SAGE_MANIFEST:?missing frozen E14 SAGE manifest}"
: "${SAGE_MANIFEST_SHA256:?missing E14 SAGE manifest hash}"
: "${RUN_ROOT:?missing unique E14 run root}"
: "${COMPONENT:?missing E14 SAGE component}"
case "${COMPONENT}" in subgoal|option) ;; *) exit 2 ;; esac
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STABLEWM=${ROOT}/data/stablewm
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006

test "$(sha256sum "${SAGE_MANIFEST}" | cut -d' ' -f1)" = "${SAGE_MANIFEST_SHA256}"
record=$(awk -F '\t' -v id="${SLURM_ARRAY_TASK_ID}" 'NR>1 && $1==id {print $0}' "${SAGE_MANIFEST}")
test -n "${record}"
IFS=$'\t' read -r ARRAY_ID TASK SEED <<< "${record}"
test "${ARRAY_ID}" = "${SLURM_ARRAY_TASK_ID}"

case "${TASK}" in
  pusht) ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; CACHE_JOB=298993-0 ;;
  cube) ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; CACHE_JOB=298993-1 ;;
  *) exit 2 ;;
esac
BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
CACHE=${BASE}/e14-variable-cache-job-${CACHE_JOB}
OUT=${RUN_ROOT}/sage/${COMPONENT}/${TASK}/seed-${SEED}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"
extra=()
if [[ "${COMPONENT}" = option ]]; then
  SUBGOAL=${RUN_ROOT}/sage/subgoal/${TASK}/seed-${SEED}/best.pt
  test -f "${SUBGOAL}"
  extra=(--subgoal-checkpoint "${SUBGOAL}")
fi

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/train_gdp_cem_e14_sage.py" \
  --task "${TASK}" --component "${COMPONENT}" --seed "${SEED}" \
  --latent-h5 "${LATENT}/latents.h5" \
  --latent-manifest "${LATENT}/manifest.json" \
  --cache-h5 "${CACHE}/cache.h5" \
  --cache-manifest "${CACHE}/manifest.json" \
  "${extra[@]}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUT}"
sha256sum "${OUT}/best.pt" "${OUT}/training.jsonl" "${OUT}/summary.json" > "${OUT}/sha256.txt"
