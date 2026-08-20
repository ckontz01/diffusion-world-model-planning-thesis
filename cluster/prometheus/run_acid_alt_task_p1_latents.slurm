#!/usr/bin/env bash

# Extract the complete frozen P1 latent cache for one canonical Le-WM task.

#SBATCH --job-name=acid-alt-task-latents
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-latents-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-latents-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-latents-${SLURM_JOB_ID}"

eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" \
  -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"
CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"
PARTITIONS="${ROOT}/manifests/partitions/${TASK}-v1/episodes-seed-20260728.tsv"
OUTPUT="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/p1-flat-latents-job-${SLURM_JOB_ID}"
for required in "${IMAGE}" "${SOURCE_MANIFEST}" "${DATASET}" "${CHECKPOINT}" \
  "${PARTITIONS}"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  STABLEWM_HOME="${STABLEWM_HOME}" TMPDIR="${JOB_TMP}" \
  python -m acid_alternative.extract_flat_latents \
  --stablewm-home "${STABLEWM_HOME}" --dataset "${DATASET}" \
  --partition-manifest "${PARTITIONS}" --partition P1 \
  --policy "${WORLD_MODEL_POLICY}" --checkpoint-file "${CHECKPOINT}" \
  --source-manifest "${SOURCE_MANIFEST}" --seed 42 --batch-size 256 \
  --output-h5 "${OUTPUT}/latents.h5" --output-json "${OUTPUT}/manifest.json"
printf '%s\n' "task=${TASK}" "job_id=${SLURM_JOB_ID}" \
  "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${OUTPUT}/provenance.txt"
sha256sum "${SOURCE_MANIFEST}" "${OUTPUT}/latents.h5" "${OUTPUT}/manifest.json" \
  "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
