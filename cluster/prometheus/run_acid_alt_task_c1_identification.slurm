#!/usr/bin/env bash

# Never-used, episode-disjoint I1 identification for learned transition scorers.

#SBATCH --job-name=acid-alt-task-c1-id
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --array=0-8%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-c1-id-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-c1-id-%A_%a.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${ORCH_SNAPSHOT:?submit with immutable orchestration snapshot path}"
: "${CORE_SCORER_JOB_ID:?submit with core scorer array ID}"
: "${CONTROL_JOB_ID:?submit with control scorer array ID}"
: "${I1_LATENT_JOB_ID:?submit with I1 latent job ID}"
: "${I1_TRANSITION_JOB_ID:?submit with I1 transition-cache job ID}"
: "${TRAINING_TRANSITION_JOB_ID:?submit with frozen P1 transition-cache job ID}"
: "${CONFIRMATION_AUTHORIZATION:?submit with immutable C1 authorization}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
ANALYSIS_MANIFEST="${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"
ORCHESTRATION_MANIFEST="${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
I1_LATENT_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/i1-flat-latents-job-${I1_LATENT_JOB_ID}"
I1_TRANSITION_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/i1-transition-cache-job-${I1_TRANSITION_JOB_ID}"
TRAINING_TRANSITION_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/transition-cache-job-${TRAINING_TRANSITION_JOB_ID}"
WORLD_CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"
EVAL_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/c1-locked-confirmation.tsv"
IDENTIFICATION_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-episodes.tsv"
IDENTIFICATION_SUMMARY="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-summary.json"
SEEDS=(6101 6102 6103)
group=$((SLURM_ARRAY_TASK_ID / 3)); seed_index=$((SLURM_ARRAY_TASK_ID % 3)); SEED="${SEEDS[${seed_index}]}"
case "${group}" in
  0) MODEL=diffusion; CONDITION=true; ARM=diffusion; VARIANT=diffusion; SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/diffusion/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-$((3 + seed_index))/best.pt" ;;
  1) MODEL=forward; CONDITION=true; ARM=forward; VARIANT=forward; SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-$((6 + seed_index))/best.pt" ;;
  2) MODEL=diffusion; CONDITION=shuffled_action; ARM=diffusion; VARIANT=diffusion_shuffled; SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/diffusion/shuffled_action/seed-${SEED}-job-${CONTROL_JOB_ID}-${seed_index}/best.pt" ;;
  *) exit 2 ;;
esac
for required in "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${IMAGE}" "${CONFIRMATION_AUTHORIZATION}" "${WORLD_CHECKPOINT}" "${EVAL_MANIFEST}" "${IDENTIFICATION_MANIFEST}" "${IDENTIFICATION_SUMMARY}" "${I1_LATENT_DIR}/latents.h5" "${I1_LATENT_DIR}/manifest.json" "${I1_TRANSITION_DIR}/transitions.h5" "${I1_TRANSITION_DIR}/manifest.json" "${TRAINING_TRANSITION_DIR}/transitions.h5" "${TRAINING_TRANSITION_DIR}/manifest.json" "${SCORER}"; do test -f "${required}"; done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.verify_c1_authorization --authorization "${CONFIRMATION_AUTHORIZATION}" --task "${TASK}" --arm "${ARM}" --scorer-variant "${VARIANT}" --seed "${SEED}" --source-manifest "${SOURCE_MANIFEST}" --analysis-manifest "${ANALYSIS_MANIFEST}" --orchestration-manifest "${ORCHESTRATION_MANIFEST}" --eval-manifest "${EVAL_MANIFEST}" --world-model-checkpoint "${WORLD_CHECKPOINT}" --identification-manifest "${IDENTIFICATION_MANIFEST}" --identification-summary "${IDENTIFICATION_SUMMARY}" --scorer-checkpoint "${SCORER}"
OUTPUT="${ROOT}/results/acid-alternative/identification/c1/${TASK}/${MODEL}/${CONDITION}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-c1-id-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"; trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" -m acid_alternative.evaluate_transition_identification --task "${TASK}" --checkpoint "${SCORER}" --latent-h5 "${I1_LATENT_DIR}/latents.h5" --latent-manifest "${I1_LATENT_DIR}/manifest.json" --training-transition-h5 "${TRAINING_TRANSITION_DIR}/transitions.h5" --training-transition-manifest "${TRAINING_TRANSITION_DIR}/manifest.json" --identification-transition-h5 "${I1_TRANSITION_DIR}/transitions.h5" --identification-transition-manifest "${I1_TRANSITION_DIR}/manifest.json" --identification-episode-manifest "${IDENTIFICATION_MANIFEST}" --source-manifest "${SOURCE_MANIFEST}" --confirmation-authorization "${CONFIRMATION_AUTHORIZATION}" --device cuda --batch-size 4096 --output-dir "${OUTPUT}"
printf '%s\n' "task=${TASK}" "model=${MODEL}" "condition=${CONDITION}" "variant=${VARIANT}" "seed=${SEED}" "i1_latent_job=${I1_LATENT_JOB_ID}" "i1_transition_job=${I1_TRANSITION_JOB_ID}" "training_transition_job=${TRAINING_TRANSITION_JOB_ID}" "authorization=${CONFIRMATION_AUTHORIZATION}" "job_id=${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${CONFIRMATION_AUTHORIZATION}" "${IDENTIFICATION_MANIFEST}" "${IDENTIFICATION_SUMMARY}" "${I1_LATENT_DIR}/manifest.json" "${I1_TRANSITION_DIR}/manifest.json" "${TRAINING_TRANSITION_DIR}/manifest.json" "${OUTPUT}/summary.json" "${OUTPUT}/identification-examples.npz" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
