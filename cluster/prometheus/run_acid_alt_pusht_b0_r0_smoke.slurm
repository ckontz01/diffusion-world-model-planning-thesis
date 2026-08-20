#!/usr/bin/env bash

# Real evaluator smoke: all frozen R0 starts, but only 4 candidates x 1 CEM
# iteration and one 25-step plan. Scientific R0 uses the full 300x30 budget.

#SBATCH --job-name=acid-alt-b0-r0-smoke
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-b0-r0-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-b0-r0-smoke-%j.err

set -euo pipefail

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
OUTPUT="${ROOT}/results/acid-alternative/preflight/pusht-b0-r0-evaluator-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-b0-r0-smoke-${SLURM_JOB_ID}"

for required in \
  "${IMAGE}" "${SOURCE_MANIFEST}" "${DATASET}" "${CHECKPOINT}" "${MANIFEST}"; do
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
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export SLURM_JOB_ID="'"${SLURM_JOB_ID}"'"
    export TMPDIR="'"${JOB_TMP}"'"
    python -m acid_alternative.evaluate_matched \
      --arm b0 \
      --code-root "'"${CODE}"'" \
      --eval-config-name pusht \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --dataset "'"${DATASET}"'" \
      --dataset-name pusht_expert_train \
      --world-model-policy pusht/lewm_hf_22b330c \
      --world-model-checkpoint "'"${CHECKPOINT}"'" \
      --source-manifest "'"${SOURCE_MANIFEST}"'" \
      --eval-manifest "'"${MANIFEST}"'" \
      --planner-seed 7101 \
      --goal-offset 25 \
      --eval-budget 25 \
      --horizon 5 \
      --receding-horizon 5 \
      --action-block 5 \
      --cem-samples 4 \
      --cem-steps 1 \
      --cem-topk 2 \
      --output-dir "'"${OUTPUT}"'"
  '

mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
sha256sum "${OUTPUT}/summary.json" "${OUTPUT}/episodes.tsv" \
  "${OUTPUT}/resolved-config.json" "${OUTPUT}/cem-diagnostics.jsonl" \
  > "${OUTPUT}/sha256.txt"
