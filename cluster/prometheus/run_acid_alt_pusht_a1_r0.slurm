#!/usr/bin/env bash

# Paired native-ACID reproduction on the official PushT R0 starts.

#SBATCH --job-name=acid-alt-pusht-a1-r0
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --array=0-2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-a1-r0-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-a1-r0-%A_%a.err

set -euo pipefail

: "${SCORER_JOB_ID:?submit with --export=ALL,SCORER_JOB_ID=<core scorer array job>}"
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
MANIFEST="${ROOT}/manifests/acid-alternative-v1/pusht/r0-official-seed42.tsv"
SEEDS=(6101 6102 6103)
SEED="${SEEDS[${SLURM_ARRAY_TASK_ID}]}"
SCORER="${ROOT}/results/acid-alternative/scorers/pusht/acid/true/seed-${SEED}-job-${SCORER_JOB_ID}-${SLURM_ARRAY_TASK_ID}/best.pt"
OUTPUT="${ROOT}/results/acid-alternative/r0/pusht/acid/train-seed-${SEED}-planner-seed-42-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-a1-r0-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

for required in \
  "${IMAGE}" "${SOURCE_MANIFEST}" "${DATASET}" "${CHECKPOINT}" "${MANIFEST}" \
  "${SCORER}"; do
  test -f "${required}"
done
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

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONPATH="'"${SNAPSHOT}"':'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export PYTHONHASHSEED=42
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export SLURM_JOB_ID="'"${SLURM_ARRAY_JOB_ID}"'_'"${SLURM_ARRAY_TASK_ID}"'"
    export TMPDIR="'"${JOB_TMP}"'"
    python -m acid_alternative.evaluate_matched \
      --arm acid \
      --code-root "'"${CODE}"'" \
      --eval-config-name pusht \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --dataset "'"${DATASET}"'" \
      --dataset-name pusht_expert_train \
      --world-model-policy pusht/lewm_hf_22b330c \
      --world-model-checkpoint "'"${CHECKPOINT}"'" \
      --source-manifest "'"${SOURCE_MANIFEST}"'" \
      --scorer-checkpoint "'"${SCORER}"'" \
      --eval-manifest "'"${MANIFEST}"'" \
      --planner-seed 42 \
      --lambda-weight 0.07 \
      --goal-offset 25 \
      --eval-budget 50 \
      --horizon 5 \
      --receding-horizon 5 \
      --action-block 5 \
      --cem-samples 300 \
      --cem-steps 30 \
      --cem-topk 30 \
      --output-dir "'"${OUTPUT}"'"
  '

mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
printf '%s\n' \
  "array_job_id=${SLURM_ARRAY_JOB_ID}" \
  "array_task_id=${SLURM_ARRAY_TASK_ID}" \
  "training_seed=${SEED}" \
  "planner_seed=42" \
  "node=$(hostname)" \
  > "${OUTPUT}/provenance.txt"
sha256sum "${OUTPUT}/summary.json" "${OUTPUT}/episodes.tsv" \
  "${OUTPUT}/resolved-config.json" "${OUTPUT}/cem-diagnostics.jsonl" \
  "${OUTPUT}/source-provenance.sha256" "${OUTPUT}/provenance.txt" \
  > "${OUTPUT}/sha256.txt"
