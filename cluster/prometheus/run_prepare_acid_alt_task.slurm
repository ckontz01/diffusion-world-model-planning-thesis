#!/usr/bin/env bash

# Freeze master/P1/evaluation manifests for one canonical Le-WM task. For
# Reacher and Cube this also creates the canonical StableWorldModel dataset
# alias expected by the released eval config, without duplicating dataset bytes.

#SBATCH --job-name=acid-alt-prepare-task
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-prepare-task-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-prepare-task-%j.err

set -euo pipefail

: "${TASK:?submit with --export=ALL,TASK=pusht|reacher|cube}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
STABLEWM_HOME="${ROOT}/data/stablewm"
JOB_TMP="/tmp/ckontzias-acid-alt-prepare-${TASK}-${SLURM_JOB_ID}"

case "${TASK}" in
  pusht)
    STAGED_DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
    ;;
  reacher)
    STAGED_DATASET="${STABLEWM_HOME}/reacher.h5"
    ;;
  cube)
    STAGED_DATASET="${STABLEWM_HOME}/cube_single_expert.h5"
    ;;
  *)
    echo "Unknown TASK: ${TASK}" >&2
    exit 2
    ;;
esac

for required in "${IMAGE}" "${SOURCE_MANIFEST}" "${STAGED_DATASET}"; do
  test -f "${required}"
done
mkdir -p "${JOB_TMP}"
trap 'rm -rf -- "${JOB_TMP}"' EXIT

eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" \
  "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec \
  "${TASK}" --format shell)"

CANONICAL_DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"
mkdir -p "$(dirname "${CANONICAL_DATASET}")"
if [[ "${STAGED_DATASET}" != "${CANONICAL_DATASET}" ]]; then
  if [[ -e "${CANONICAL_DATASET}" ]]; then
    if [[ ! "${STAGED_DATASET}" -ef "${CANONICAL_DATASET}" ]]; then
      echo "Canonical dataset path exists but is not the staged dataset" >&2
      exit 2
    fi
  else
    ln "${STAGED_DATASET}" "${CANONICAL_DATASET}"
  fi
fi
[[ "${STAGED_DATASET}" -ef "${CANONICAL_DATASET}" ]]

PARTITION_DIR="${ROOT}/manifests/partitions/${TASK}-v1"
MASTER="${PARTITION_DIR}/episodes-seed-20260728.tsv"
MASTER_JSON="${PARTITION_DIR}/episodes-seed-20260728-summary.json"
P1="${PARTITION_DIR}/p1-train-val-seed-20260728.tsv"
P1_JSON="${PARTITION_DIR}/p1-train-val-seed-20260728-summary.json"
EVAL_DIR="${ROOT}/manifests/acid-alternative-v1/${TASK}"
if [[ -e "${PARTITION_DIR}" && ! -e "${EVAL_DIR}" ]] || \
   [[ ! -e "${PARTITION_DIR}" && -e "${EVAL_DIR}" ]]; then
  echo "Refusing partial frozen manifest state for ${TASK}" >&2
  exit 2
fi
CREATED=false
I1_CREATED=false
if [[ ! -e "${PARTITION_DIR}" ]]; then
  CREATED=true
  mkdir -p "${PARTITION_DIR}"

  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" \
    "${ENV_DIR}/bin/python" -m acid_alternative.create_episode_partitions \
    --dataset "${CANONICAL_DATASET}" \
    --dataset-name "${DATASET_NAME}" --seed 20260728 \
    --output-tsv "${MASTER}" --output-json "${MASTER_JSON}"

  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" \
    "${ENV_DIR}/bin/python" -m acid_alternative.create_p1_split \
    --partition-manifest "${MASTER}" \
    --dataset-name "${DATASET_NAME}" --seed 20260728 \
    --output-tsv "${P1}" --output-json "${P1_JSON}"

legacy_arguments=(
  --legacy-root "${ROOT}/data/stablewm/repro"
  --legacy-root "${ROOT}/candidate-results"
  --legacy-root "${ROOT}/data/stablewm/derived/candidate-pools/${TASK}-v1"
  --legacy-root "${ROOT}/data/stablewm/derived/candidate-executions/${TASK}-v1"
  --legacy-root "${ROOT}/data/stablewm/derived/closed-loop-confirmation/${TASK}-v1"
)
for other in pusht reacher cube tworoom; do
  if [[ "${other}" != "${TASK}" ]]; then
    legacy_arguments+=(--legacy-exclude-path-token "${other}")
  fi
done
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" \
    "${ENV_DIR}/bin/python" -m acid_alternative.create_eval_manifests \
    --dataset "${CANONICAL_DATASET}" --task "${TASK}" \
    --partition-manifest "${MASTER}" --goal-offset 25 \
    --output-dir "${EVAL_DIR}" "${legacy_arguments[@]}"

  printf '%s\n' \
    "task=${TASK}" \
    "canonical_dataset=${CANONICAL_DATASET}" \
    "staged_dataset=${STAGED_DATASET}" \
    "same_inode=true" \
    "job_id=${SLURM_JOB_ID}" \
    "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "${PARTITION_DIR}/provenance.txt"
  sha256sum "$0" "${SOURCE_MANIFEST}" "${CANONICAL_DATASET}" "${MASTER}" \
    "${MASTER_JSON}" "${P1}" "${P1_JSON}" \
    "${EVAL_DIR}"/*.tsv "${EVAL_DIR}/summary.json" \
    > "${PARTITION_DIR}/sha256.txt"
fi

I1="${EVAL_DIR}/i1-confirmation-identification-episodes.tsv"
I1_JSON="${EVAL_DIR}/i1-confirmation-identification-summary.json"
if [[ -e "${I1}" && ! -e "${I1_JSON}" ]] || [[ ! -e "${I1}" && -e "${I1_JSON}" ]]; then
  echo "Refusing partial I1 manifest state for ${TASK}" >&2
  exit 2
fi
if [[ ! -e "${I1}" ]]; then
  I1_CREATED=true
  i1_legacy_arguments=(
    --legacy-root "${ROOT}/data/stablewm/repro"
    --legacy-root "${ROOT}/candidate-results"
    --legacy-root "${ROOT}/data/stablewm/derived/candidate-pools/${TASK}-v1"
    --legacy-root "${ROOT}/data/stablewm/derived/candidate-executions/${TASK}-v1"
    --legacy-root "${ROOT}/data/stablewm/derived/closed-loop-confirmation/${TASK}-v1"
  )
  for other in pusht reacher cube tworoom; do
    if [[ "${other}" != "${TASK}" ]]; then i1_legacy_arguments+=(--legacy-exclude-path-token "${other}"); fi
  done
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" \
    "${ENV_DIR}/bin/python" -m acid_alternative.create_identification_manifest \
    --dataset "${CANONICAL_DATASET}" --task "${TASK}" --partition-manifest "${MASTER}" \
    --evaluation-manifest "${EVAL_DIR}/r0-official-seed42.tsv" \
    --evaluation-manifest "${EVAL_DIR}/d1-fresh-development.tsv" \
    --evaluation-manifest "${EVAL_DIR}/c1-locked-confirmation.tsv" \
    --seed 2026081314 --count 200 --partition "${I1_SOURCE_PARTITION}" --frameskip 5 \
    --output-tsv "${I1}" --output-json "${I1_JSON}" "${i1_legacy_arguments[@]}"
fi

VERIFY_DIR="${ROOT}/results/acid-alternative/preparation/${TASK}/job-${SLURM_JOB_ID}"
if [[ -e "${VERIFY_DIR}" ]]; then
  echo "Refusing existing verification output: ${VERIFY_DIR}" >&2
  exit 2
fi
mkdir -p "${VERIFY_DIR}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" \
  "${ENV_DIR}/bin/python" -m acid_alternative.verify_prepared_task \
  --task "${TASK}" --dataset "${CANONICAL_DATASET}" \
  --partition-dir "${PARTITION_DIR}" --eval-dir "${EVAL_DIR}" \
  --output "${VERIFY_DIR}/verification.json"
printf '%s\n' "task=${TASK}" "created=${CREATED}" "i1_created=${I1_CREATED}" "job_id=${SLURM_JOB_ID}" \
  > "${VERIFY_DIR}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${VERIFY_DIR}/verification.json" \
  "${VERIFY_DIR}/provenance.txt" > "${VERIFY_DIR}/sha256.txt"
