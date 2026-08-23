#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-cache
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-cache-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-cache-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 cache snapshot}"
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
    ;;
  1)
    TASK=cube
    DATASET=${STABLEWM}/cube_single_expert.h5
    ARTIFACT=lewm-hf-b0747c5
    LATENT_JOB=296666
    TRANSITION_JOB=296667
    ;;
  *) exit 2 ;;
esac

BASE=${STABLEWM}/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
TRANSITION=${BASE}/transition-cache-job-${TRANSITION_JOB}
P1_ROLE=${ROOT}/manifests/partitions/${TASK}-v1/p1-train-val-seed-20260728.tsv
OUT=${BASE}/e14-variable-cache-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/build_gdp_cem_e14_variable_cache.py" \
  --task "${TASK}" --dataset "${DATASET}" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --transition-h5 "${TRANSITION}/transitions.h5" \
  --transition-manifest "${TRANSITION}/manifest.json" \
  --p1-role-manifest "${P1_ROLE}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-h5 "${OUT}/cache.h5" --output-json "${OUT}/manifest.json"

printf '%s\n' \
  'study=gdp_cem_e14_variable_cache' \
  "task=${TASK}" \
  "job_id=${SLURM_JOB_ID}" \
  'd3_metric_read=false' \
  'd4_metric_read=false' \
  'd5_read=false' \
  'protected_p3_p4_c1_i1_read=false' \
  > "${OUT}/provenance.txt"
sha256sum "${OUT}/cache.h5" "${OUT}/manifest.json" "${OUT}/provenance.txt" \
  > "${OUT}/sha256.txt"

