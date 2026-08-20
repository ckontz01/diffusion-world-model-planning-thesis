#!/usr/bin/env bash

# Frozen primary PushT development matrix: five arms by three paired seeds.

#SBATCH --job-name=acid-alt-pusht-d1-primary
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --array=0-14%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-primary-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-primary-%A_%a.err

set -euo pipefail

: "${CORE_SCORER_JOB_ID:?submit with core scorer array job ID}"
: "${REACHABILITY_JOB_ID:?submit with reachability array job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
SOURCE_MANIFEST="${SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
CHECKPOINT="${STABLEWM_HOME}/pusht/lewm_hf_22b330c_object.ckpt"
MANIFEST="${ROOT}/manifests/acid-alternative-v1/pusht/d1-fresh-development.tsv"
ARMS=(b0 acid reachability diffusion forward)
SEEDS=(6101 6102 6103)
PLANNER_SEEDS=(7101 7102 7103)
ARM_INDEX=$((SLURM_ARRAY_TASK_ID / 3))
SEED_INDEX=$((SLURM_ARRAY_TASK_ID % 3))
ARM="${ARMS[${ARM_INDEX}]}"
SEED="${SEEDS[${SEED_INDEX}]}"
PLANNER_SEED="${PLANNER_SEEDS[${SEED_INDEX}]}"
SCORER=""
SCORER_TASK=""
case "${ARM}" in
  b0)
    ;;
  acid)
    SCORER_TASK="${SEED_INDEX}"
    SCORER="${ROOT}/results/acid-alternative/scorers/pusht/acid/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-${SCORER_TASK}/best.pt"
    ;;
  reachability)
    SCORER_TASK="${SEED_INDEX}"
    SCORER="${ROOT}/results/acid-alternative/scorers/pusht/reachability/true/seed-${SEED}-job-${REACHABILITY_JOB_ID}-${SCORER_TASK}/best.pt"
    ;;
  diffusion)
    SCORER_TASK="$((3 + SEED_INDEX))"
    SCORER="${ROOT}/results/acid-alternative/scorers/pusht/diffusion/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-${SCORER_TASK}/best.pt"
    ;;
  forward)
    SCORER_TASK="$((6 + SEED_INDEX))"
    SCORER="${ROOT}/results/acid-alternative/scorers/pusht/forward/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-${SCORER_TASK}/best.pt"
    ;;
  *)
    echo "Unknown arm ${ARM}" >&2
    exit 2
    ;;
esac
OUTPUT="${ROOT}/results/acid-alternative/d1/pusht/${ARM}/train-seed-${SEED}-planner-seed-${PLANNER_SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-d1-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

for required in \
  "${IMAGE}" "${SOURCE_MANIFEST}" "${DATASET}" "${CHECKPOINT}" "${MANIFEST}"; do
  test -f "${required}"
done
if [[ -n "${SCORER}" ]]; then
  test -f "${SCORER}"
fi
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
sha256sum "$0" "${SOURCE_MANIFEST}" > "${JOB_TMP}/source-provenance.sha256"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
nvidia-smi

SCORER_ARGUMENT=()
if [[ -n "${SCORER}" ]]; then
  SCORER_ARGUMENT=(--scorer-checkpoint "${SCORER}")
fi
apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -s -- \
    "${ARM}" "${SEED}" "${PLANNER_SEED}" "${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" \
    "${JOB_TMP}" "${SNAPSHOT}" "${CODE}" "${TOOLS_DIR}" "${ENV_DIR}" \
    "${STABLEWM_HOME}" "${DATASET}" "${CHECKPOINT}" "${SOURCE_MANIFEST}" \
    "${MANIFEST}" "${OUTPUT}" "${SCORER}" <<'CONTAINER'
set -euo pipefail
ARM="$1"
SEED="$2"
PLANNER_SEED="$3"
RUN_JOB_ID="$4"
JOB_TMP="$5"
SNAPSHOT="$6"
CODE="$7"
TOOLS_DIR="$8"
ENV_DIR="$9"
STABLEWM_HOME="${10}"
DATASET="${11}"
CHECKPOINT="${12}"
SOURCE_MANIFEST="${13}"
MANIFEST="${14}"
OUTPUT="${15}"
SCORER="${16}"
export PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm"
export PYTHONHASHSEED="${PLANNER_SEED}"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export SLURM_JOB_ID="${RUN_JOB_ID}"
export TMPDIR="${JOB_TMP}"
arguments=(
  --arm "${ARM}"
  --code-root "${CODE}"
  --eval-config-name pusht
  --stablewm-home "${STABLEWM_HOME}"
  --dataset "${DATASET}"
  --dataset-name pusht_expert_train
  --world-model-policy pusht/lewm_hf_22b330c
  --world-model-checkpoint "${CHECKPOINT}"
  --source-manifest "${SOURCE_MANIFEST}"
  --eval-manifest "${MANIFEST}"
  --planner-seed "${PLANNER_SEED}"
  --lambda-weight 0.07
  --goal-offset 25
  --eval-budget 50
  --horizon 5
  --receding-horizon 5
  --action-block 5
  --cem-samples 300
  --cem-steps 30
  --cem-topk 30
  --output-dir "${OUTPUT}"
)
if [[ -n "${SCORER}" ]]; then
  arguments+=(--scorer-checkpoint "${SCORER}")
fi
python -m acid_alternative.evaluate_matched "${arguments[@]}"
CONTAINER

mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
printf '%s\n' \
  "array_job_id=${SLURM_ARRAY_JOB_ID}" \
  "array_task_id=${SLURM_ARRAY_TASK_ID}" \
  "arm=${ARM}" \
  "training_seed=${SEED}" \
  "planner_seed=${PLANNER_SEED}" \
  "scorer_array_task=${SCORER_TASK}" \
  "node=$(hostname)" \
  > "${OUTPUT}/provenance.txt"
sha256sum "${OUTPUT}/summary.json" "${OUTPUT}/episodes.tsv" \
  "${OUTPUT}/resolved-config.json" "${OUTPUT}/cem-diagnostics.jsonl" \
  "${OUTPUT}/source-provenance.sha256" "${OUTPUT}/provenance.txt" \
  > "${OUTPUT}/sha256.txt"
