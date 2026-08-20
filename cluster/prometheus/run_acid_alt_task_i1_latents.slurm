#!/usr/bin/env bash

# Encode the authorized, episode-disjoint I1 confirmation-identification set.

#SBATCH --job-name=acid-alt-task-i1-latents
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-i1-latents-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-i1-latents-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${ORCH_SNAPSHOT:?submit with immutable orchestration snapshot path}"
: "${CONFIRMATION_AUTHORIZATION:?submit with immutable C1 authorization}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"; ANALYSIS_MANIFEST="${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"; ORCHESTRATION_MANIFEST="${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"; CODE="${ROOT}/src/hi-lewm"; STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"; CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"; EVAL_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/c1-locked-confirmation.tsv"; I1_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-episodes.tsv"; I1_SUMMARY="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-summary.json"
OUTPUT="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/i1-flat-latents-job-${SLURM_JOB_ID}"; JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-i1-latents-${SLURM_JOB_ID}"
for required in "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${IMAGE}" "${DATASET}" "${CHECKPOINT}" "${EVAL_MANIFEST}" "${I1_MANIFEST}" "${I1_SUMMARY}" "${CONFIRMATION_AUTHORIZATION}"; do test -f "${required}"; done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.verify_c1_authorization --authorization "${CONFIRMATION_AUTHORIZATION}" --task "${TASK}" --arm b0 --seed 6101 --source-manifest "${SOURCE_MANIFEST}" --analysis-manifest "${ANALYSIS_MANIFEST}" --orchestration-manifest "${ORCHESTRATION_MANIFEST}" --eval-manifest "${EVAL_MANIFEST}" --world-model-checkpoint "${CHECKPOINT}" --identification-manifest "${I1_MANIFEST}" --identification-summary "${I1_SUMMARY}"
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"; trap 'rm -rf -- "${JOB_TMP}"' EXIT; export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"; nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" PYTHONHASHSEED=42 CUBLAS_WORKSPACE_CONFIG=:4096:8 TMPDIR="${JOB_TMP}" python -m acid_alternative.extract_flat_latents --stablewm-home "${STABLEWM_HOME}" --dataset "${DATASET}" --partition-manifest "${I1_MANIFEST}" --partition I1 --policy "${WORLD_MODEL_POLICY}" --checkpoint-file "${CHECKPOINT}" --source-manifest "${SOURCE_MANIFEST}" --seed 42 --batch-size 256 --output-h5 "${OUTPUT}/latents.h5" --output-json "${OUTPUT}/manifest.json"
printf '%s\n' "task=${TASK}" "authorization=${CONFIRMATION_AUTHORIZATION}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${CONFIRMATION_AUTHORIZATION}" "${I1_MANIFEST}" "${I1_SUMMARY}" "${OUTPUT}/latents.h5" "${OUTPUT}/manifest.json" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
