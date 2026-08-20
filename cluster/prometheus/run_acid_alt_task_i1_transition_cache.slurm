#!/usr/bin/env bash

# Build I1 action/latent pairs with only the frozen P1-training statistics.

#SBATCH --job-name=acid-alt-task-i1-cache
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-i1-cache-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-i1-cache-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"; : "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"; : "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"; : "${ORCH_SNAPSHOT:?submit with immutable orchestration snapshot path}"; : "${I1_LATENT_JOB_ID:?submit with I1 latent job ID}"; : "${TRAINING_TRANSITION_JOB_ID:?submit with P1 transition job ID}"; : "${CONFIRMATION_AUTHORIZATION:?submit with immutable C1 authorization}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"; ANALYSIS_MANIFEST="${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"; ORCHESTRATION_MANIFEST="${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"; CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"; EVAL_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/c1-locked-confirmation.tsv"; I1_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-episodes.tsv"; I1_SUMMARY="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-summary.json"
I1_LATENT="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/i1-flat-latents-job-${I1_LATENT_JOB_ID}"; TRAINING="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/transition-cache-job-${TRAINING_TRANSITION_JOB_ID}"; OUTPUT="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/i1-transition-cache-job-${SLURM_JOB_ID}"
for required in "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${IMAGE}" "${DATASET}" "${CHECKPOINT}" "${EVAL_MANIFEST}" "${I1_MANIFEST}" "${I1_SUMMARY}" "${CONFIRMATION_AUTHORIZATION}" "${I1_LATENT}/latents.h5" "${I1_LATENT}/manifest.json" "${TRAINING}/transitions.h5" "${TRAINING}/manifest.json"; do test -f "${required}"; done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.verify_c1_authorization --authorization "${CONFIRMATION_AUTHORIZATION}" --task "${TASK}" --arm b0 --seed 6101 --source-manifest "${SOURCE_MANIFEST}" --analysis-manifest "${ANALYSIS_MANIFEST}" --orchestration-manifest "${ORCHESTRATION_MANIFEST}" --eval-manifest "${EVAL_MANIFEST}" --world-model-checkpoint "${CHECKPOINT}" --identification-manifest "${I1_MANIFEST}" --identification-summary "${I1_SUMMARY}"
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi; mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.build_identification_transition_cache --task "${TASK}" --dataset "${DATASET}" --latent-h5 "${I1_LATENT}/latents.h5" --latent-manifest "${I1_LATENT}/manifest.json" --identification-manifest "${I1_MANIFEST}" --training-transition-h5 "${TRAINING}/transitions.h5" --training-transition-manifest "${TRAINING}/manifest.json" --source-manifest "${SOURCE_MANIFEST}" --frameskip 5 --output-h5 "${OUTPUT}/transitions.h5" --output-json "${OUTPUT}/manifest.json"
printf '%s\n' "task=${TASK}" "i1_latent_job=${I1_LATENT_JOB_ID}" "training_transition_job=${TRAINING_TRANSITION_JOB_ID}" "authorization=${CONFIRMATION_AUTHORIZATION}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${CONFIRMATION_AUTHORIZATION}" "${I1_MANIFEST}" "${I1_SUMMARY}" "${OUTPUT}/transitions.h5" "${OUTPUT}/manifest.json" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
