#!/usr/bin/env bash

#SBATCH --job-name=acid-alt-pusht-pairs
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-pairs-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-pairs-%j.err

set -euo pipefail

: "${LATENT_JOB_ID:?submit with --export=ALL,LATENT_JOB_ID=<completed latent job>}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
SOURCE_MANIFEST="${SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
STABLEWM_HOME="${ROOT}/data/stablewm"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
ROLES="${ROOT}/manifests/partitions/pusht-v1/p1-train-val-seed-20260728.tsv"
LATENT_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/p1-flat-latents-job-${LATENT_JOB_ID}"
OUTPUT="${STABLEWM_HOME}/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/transition-cache-job-${SLURM_JOB_ID}"

for required in \
  "${IMAGE}" "${DATASET}" "${ROLES}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" "${SOURCE_MANIFEST}"; do
  test -f "${required}"
done
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}"
sha256sum "$0" "${SOURCE_MANIFEST}" > "${OUTPUT}/source-provenance.sha256"

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  "${IMAGE}" env \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" -m acid_alternative.build_transition_cache \
    --dataset "${DATASET}" \
    --latent-h5 "${LATENT_DIR}/latents.h5" \
    --latent-manifest "${LATENT_DIR}/manifest.json" \
    --p1-role-manifest "${ROLES}" \
    --source-manifest "${SOURCE_MANIFEST}" \
    --frameskip 5 \
    --output-h5 "${OUTPUT}/transitions.h5" \
    --output-json "${OUTPUT}/manifest.json"

sha256sum "${OUTPUT}/transitions.h5" "${OUTPUT}/manifest.json" > "${OUTPUT}/sha256.txt"
printf '%s\n' "latent_job_id=${LATENT_JOB_ID}" "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > "${OUTPUT}/provenance.txt"
