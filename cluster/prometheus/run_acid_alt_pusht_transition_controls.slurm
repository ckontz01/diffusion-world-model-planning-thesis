#!/usr/bin/env bash

# Diagnostic-only negative controls: shuffled actions for D1/F1 and an
# action-ablated D1, each at the three frozen scorer seeds.

#SBATCH --job-name=acid-alt-pusht-controls
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=10:00:00
#SBATCH --array=0-8%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-control-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-control-%A_%a.err

set -euo pipefail

: "${LATENT_JOB_ID:?submit with --export=ALL,LATENT_JOB_ID=<latent job>}"
: "${TRANSITION_JOB_ID:?submit with --export=ALL,TRANSITION_JOB_ID=<cache job>}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
SOURCE_MANIFEST="${SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
LATENT_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/p1-flat-latents-job-${LATENT_JOB_ID}"
TRANSITION_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/transition-cache-job-${TRANSITION_JOB_ID}"
SEEDS=(6101 6102 6103)

GROUP=$((SLURM_ARRAY_TASK_ID / 3))
SEED_INDEX=$((SLURM_ARRAY_TASK_ID % 3))
SEED="${SEEDS[${SEED_INDEX}]}"
case "${GROUP}" in
  0)
    MODEL="diffusion"
    CONDITION="shuffled_action"
    ;;
  1)
    MODEL="forward"
    CONDITION="shuffled_action"
    ;;
  2)
    MODEL="diffusion"
    CONDITION="action_ablated"
    ;;
  *)
    echo "Unknown control group: ${GROUP}" >&2
    exit 2
    ;;
esac

OUTPUT="${ROOT}/results/acid-alternative/scorers/pusht/${MODEL}/${CONDITION}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-control-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

for required in \
  "${IMAGE}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
  "${TRANSITION_DIR}/transitions.h5" "${TRANSITION_DIR}/manifest.json" \
  "${SOURCE_MANIFEST}"; do
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

printf '%s\n' \
  "array_job_id=${SLURM_ARRAY_JOB_ID}" \
  "array_task_id=${SLURM_ARRAY_TASK_ID}" \
  "model=${MODEL}" \
  "condition=${CONDITION}" \
  "seed=${SEED}" \
  "node=$(hostname)" \
  > "${JOB_TMP}/provenance.txt"
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
    export PYTHONHASHSEED="'"${SEED}"'"
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python -m acid_alternative.train_transition_scorer \
      --model "'"${MODEL}"'" \
      --condition "'"${CONDITION}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --transition-h5 "'"${TRANSITION_DIR}"'/transitions.h5" \
      --transition-manifest "'"${TRANSITION_DIR}"'/manifest.json" \
      --source-manifest "'"${SOURCE_MANIFEST}"'" \
      --output-dir "'"${OUTPUT}"'" \
      --seed "'"${SEED}"'" \
      --maximum-steps 200000 \
      --warmup-steps 1000 \
      --batch-size 256 \
      --validation-batch-size 4096 \
      --validation-interval 5000 \
      --validation-limit 100000
  '

mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
mv "${JOB_TMP}/provenance.txt" "${OUTPUT}/provenance.txt"
sha256sum "${OUTPUT}/best.pt" "${OUTPUT}/summary.json" "${OUTPUT}/training.jsonl" \
  "${OUTPUT}/validation-examples.npz" \
  > "${OUTPUT}/sha256.txt"
