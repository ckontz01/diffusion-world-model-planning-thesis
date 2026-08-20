#!/usr/bin/env bash

# Confirmatory five-arm matrix; impossible to start without the exact C1 lock.

#SBATCH --job-name=acid-alt-task-c1
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=24:00:00
#SBATCH --array=0-14%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-c1-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-c1-%A_%a.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${ORCH_SNAPSHOT:?submit with immutable orchestration snapshot path}"
: "${CORE_SCORER_JOB_ID:?submit with core scorer array ID}"
: "${REACHABILITY_JOB_ID:?submit with reachability-head array ID}"
: "${CONFIRMATION_AUTHORIZATION:?submit with the immutable C1 authorization JSON}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
ANALYSIS_MANIFEST="${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"
ORCHESTRATION_MANIFEST="${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
for required in "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${IMAGE}" "${CONFIRMATION_AUTHORIZATION}"; do test -f "${required}"; done
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"
CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"
MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/c1-locked-confirmation.tsv"
IDENTIFICATION_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-episodes.tsv"
IDENTIFICATION_SUMMARY="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-summary.json"
ARMS=(b0 acid reachability diffusion forward)
SEEDS=(6101 6102 6103)
PLANNER_SEEDS=(7101 7102 7103)
ARM_INDEX=$((SLURM_ARRAY_TASK_ID / 3))
SEED_INDEX=$((SLURM_ARRAY_TASK_ID % 3))
ARM="${ARMS[${ARM_INDEX}]}"
SEED="${SEEDS[${SEED_INDEX}]}"
PLANNER_SEED="${PLANNER_SEEDS[${SEED_INDEX}]}"
SCORER=""
case "${ARM}" in
  b0) ;;
  acid) SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-${SEED_INDEX}/best.pt" ;;
  reachability) SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/reachability/true/seed-${SEED}-job-${REACHABILITY_JOB_ID}-${SEED_INDEX}/best.pt" ;;
  diffusion) SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/diffusion/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-$((3 + SEED_INDEX))/best.pt" ;;
  forward) SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-$((6 + SEED_INDEX))/best.pt" ;;
  *) exit 2 ;;
esac
for required in "${DATASET}" "${CHECKPOINT}" "${MANIFEST}" "${IDENTIFICATION_MANIFEST}" "${IDENTIFICATION_SUMMARY}"; do test -f "${required}"; done
if [[ -n "${SCORER}" ]]; then test -f "${SCORER}"; fi
verify_arguments=(--authorization "${CONFIRMATION_AUTHORIZATION}" --task "${TASK}" --arm "${ARM}" --seed "${SEED}" --source-manifest "${SOURCE_MANIFEST}" --analysis-manifest "${ANALYSIS_MANIFEST}" --orchestration-manifest "${ORCHESTRATION_MANIFEST}" --eval-manifest "${MANIFEST}" --world-model-checkpoint "${CHECKPOINT}" --identification-manifest "${IDENTIFICATION_MANIFEST}" --identification-summary "${IDENTIFICATION_SUMMARY}")
if [[ -n "${SCORER}" ]]; then verify_arguments+=(--scorer-checkpoint "${SCORER}"); fi
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.verify_c1_authorization "${verify_arguments[@]}"
OUTPUT="${ROOT}/results/acid-alternative/c1/${TASK}/${ARM}/train-seed-${SEED}-planner-seed-${PLANNER_SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-c1-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
arguments=(--arm "${ARM}" --code-root "${CODE}" --eval-config-name "${EVAL_CONFIG_NAME}" --stablewm-home "${STABLEWM_HOME}" --dataset "${DATASET}" --dataset-name "${DATASET_NAME}" --world-model-policy "${WORLD_MODEL_POLICY}" --world-model-checkpoint "${CHECKPOINT}" --source-manifest "${SOURCE_MANIFEST}" --confirmation-authorization "${CONFIRMATION_AUTHORIZATION}" --eval-manifest "${MANIFEST}" --planner-seed "${PLANNER_SEED}" --lambda-weight 0.07 --goal-offset 25 --eval-budget 50 --horizon 5 --receding-horizon 5 --action-block 5 --cem-samples 300 --cem-steps 30 --cem-topk 30 --output-dir "${OUTPUT}")
if [[ -n "${SCORER}" ]]; then arguments+=(--scorer-checkpoint "${SCORER}"); fi
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED="${PLANNER_SEED}" CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  SLURM_JOB_ID="${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" \
  python -m acid_alternative.evaluate_matched "${arguments[@]}"
printf '%s\n' "task=${TASK}" "arm=${ARM}" "training_seed=${SEED}" "planner_seed=${PLANNER_SEED}" \
  "authorization=${CONFIRMATION_AUTHORIZATION}" "array_job_id=${SLURM_ARRAY_JOB_ID}" "array_task_id=${SLURM_ARRAY_TASK_ID}" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${CONFIRMATION_AUTHORIZATION}" \
  "${OUTPUT}/summary.json" "${OUTPUT}/episodes.tsv" "${OUTPUT}/resolved-config.json" \
  "${OUTPUT}/cem-diagnostics.jsonl" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
