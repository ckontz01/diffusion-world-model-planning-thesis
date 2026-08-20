#!/usr/bin/env bash

# Train faithful native A1 plus D1/F1 at the three frozen seeds.

#SBATCH --job-name=acid-alt-task-scorers
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --array=0-8%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-scorer-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-scorer-%A_%a.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${LATENT_JOB_ID:?submit with latent job ID}"
: "${TRANSITION_JOB_ID:?submit with transition-cache job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" \
  -m acid_alternative.print_task_spec "${TASK}" --format shell)"
LATENT_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/p1-flat-latents-job-${LATENT_JOB_ID}"
TRANSITION_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/transition-cache-job-${TRANSITION_JOB_ID}"
MODELS=(acid diffusion forward); SEEDS=(6101 6102 6103)
MODEL="${MODELS[$((SLURM_ARRAY_TASK_ID / 3))]}"
SEED="${SEEDS[$((SLURM_ARRAY_TASK_ID % 3))]}"
OUTPUT="${ROOT}/results/acid-alternative/scorers/${TASK}/${MODEL}/true/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-scorer-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
for required in "${IMAGE}" "${SOURCE_MANIFEST}" "${LATENT_DIR}/latents.h5" \
  "${LATENT_DIR}/manifest.json" "${TRANSITION_DIR}/transitions.h5" \
  "${TRANSITION_DIR}/manifest.json"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED="${SEED}" CUBLAS_WORKSPACE_CONFIG=:4096:8 TMPDIR="${JOB_TMP}" \
  python -m acid_alternative.train_transition_scorer --model "${MODEL}" \
  --condition true --latent-h5 "${LATENT_DIR}/latents.h5" \
  --latent-manifest "${LATENT_DIR}/manifest.json" \
  --transition-h5 "${TRANSITION_DIR}/transitions.h5" \
  --transition-manifest "${TRANSITION_DIR}/manifest.json" \
  --source-manifest "${SOURCE_MANIFEST}" --output-dir "${OUTPUT}" --seed "${SEED}" \
  --maximum-steps 200000 --warmup-steps 1000 --batch-size 256 \
  --validation-batch-size 4096 --validation-interval 5000 --validation-limit 100000
printf '%s\n' "task=${TASK}" "model=${MODEL}" "condition=true" "seed=${SEED}" \
  "array_job_id=${SLURM_ARRAY_JOB_ID}" "array_task_id=${SLURM_ARRAY_TASK_ID}" \
  "node=$(hostname)" > "${OUTPUT}/provenance.txt"
sha256sum "${SOURCE_MANIFEST}" "${OUTPUT}/best.pt" "${OUTPUT}/summary.json" \
  "${OUTPUT}/training.jsonl" "${OUTPUT}/validation-examples.npz" \
  "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
