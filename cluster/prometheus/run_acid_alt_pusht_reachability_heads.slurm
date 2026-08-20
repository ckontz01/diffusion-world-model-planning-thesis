#!/usr/bin/env bash

#SBATCH --job-name=acid-alt-pusht-trm
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --array=0-5%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-trm-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-trm-%A_%a.err

set -euo pipefail

: "${LATENT_JOB_ID:?submit with --export=ALL,LATENT_JOB_ID=<latent job>}"
: "${TRANSITION_JOB_ID:?submit with --export=ALL,TRANSITION_JOB_ID=<cache job>}"
: "${PAIR_JOB_ID:?submit with --export=ALL,PAIR_JOB_ID=<TRM pair job>}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
SOURCE_MANIFEST="${SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
STABLEWM_HOME="${ROOT}/data/stablewm"
LATENT_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/p1-flat-latents-job-${LATENT_JOB_ID}"
TRANSITION_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/transition-cache-job-${TRANSITION_JOB_ID}"
PAIR_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/reachability-pairs-job-${PAIR_JOB_ID}"
SEEDS=(6101 6102 6103)
if (( SLURM_ARRAY_TASK_ID < 3 )); then
  CONDITION="true"
  SEED_INDEX="${SLURM_ARRAY_TASK_ID}"
else
  CONDITION="shuffled_label"
  SEED_INDEX="$((SLURM_ARRAY_TASK_ID - 3))"
fi
SEED="${SEEDS[${SEED_INDEX}]}"
OUTPUT="${ROOT}/results/acid-alternative/scorers/pusht/reachability/${CONDITION}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-trm-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

for required in \
  "${IMAGE}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" \
  "${TRANSITION_DIR}/transitions.h5" "${TRANSITION_DIR}/manifest.json" \
  "${PAIR_DIR}/pairs.h5" "${PAIR_DIR}/manifest.json" "${SOURCE_MANIFEST}"; do
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
    export PYTHONPATH="'"${SNAPSHOT}"'"
    export PYTHONHASHSEED="'"${SEED}"'"
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python -m acid_alternative.train_reachability_head \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --pair-h5 "'"${PAIR_DIR}"'/pairs.h5" \
      --pair-manifest "'"${PAIR_DIR}"'/manifest.json" \
      --transition-h5 "'"${TRANSITION_DIR}"'/transitions.h5" \
      --transition-manifest "'"${TRANSITION_DIR}"'/manifest.json" \
      --source-manifest "'"${SOURCE_MANIFEST}"'" \
      --output-dir "'"${OUTPUT}"'" \
      --condition "'"${CONDITION}"'" \
      --seed "'"${SEED}"'" \
      --device cuda \
      --target-scale 224 \
      --learning-rate 0.001 \
      --weight-decay 0.0001 \
      --batch-size 1024 \
      --maximum-epochs 200 \
      --patience 20
  '

mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
mv "${JOB_TMP}/provenance.txt" "${OUTPUT}/provenance.txt"
sha256sum "${OUTPUT}/best.pt" "${OUTPUT}/summary.json" "${OUTPUT}/training.jsonl" \
  > "${OUTPUT}/sha256.txt"
