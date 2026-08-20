#!/usr/bin/env bash

# Freeze R1 pair labels: published PushT task distance; temporal elsewhere.

#SBATCH --job-name=acid-alt-task-trm-pairs
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-trm-pairs-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-trm-pairs-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${LATENT_JOB_ID:?submit with completed latent job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" \
  -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"
ROLES="${ROOT}/manifests/partitions/${TASK}-v1/p1-train-val-seed-20260728.tsv"
LATENT_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/p1-flat-latents-job-${LATENT_JOB_ID}"
OUTPUT="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/reachability-pairs-job-${SLURM_JOB_ID}"
for required in "${IMAGE}" "${SOURCE_MANIFEST}" "${DATASET}" "${ROLES}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi
mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" \
  "${ENV_DIR}/bin/python" -m acid_alternative.build_reachability_pairs \
  --dataset "${DATASET}" --latent-h5 "${LATENT_DIR}/latents.h5" \
  --latent-manifest "${LATENT_DIR}/manifest.json" --p1-role-manifest "${ROLES}" \
  --source-manifest "${SOURCE_MANIFEST}" --target "${REACHABILITY_TARGET}" \
  --train-pairs 100000 --validation-pairs 10000 --seed 20260813 \
  --output-h5 "${OUTPUT}/pairs.h5" --output-json "${OUTPUT}/manifest.json"
printf '%s\n' "task=${TASK}" "target=${REACHABILITY_TARGET}" \
  "latent_job_id=${LATENT_JOB_ID}" "job_id=${SLURM_JOB_ID}" \
  "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${OUTPUT}/provenance.txt"
sha256sum "${SOURCE_MANIFEST}" "${OUTPUT}/pairs.h5" "${OUTPUT}/manifest.json" \
  "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
