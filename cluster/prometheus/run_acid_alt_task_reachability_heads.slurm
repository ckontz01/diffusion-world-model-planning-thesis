#!/usr/bin/env bash

# Train true and shuffled-label R1 heads at three frozen seeds.

#SBATCH --job-name=acid-alt-task-trm
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --array=0-5%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-trm-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-trm-%A_%a.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${LATENT_JOB_ID:?submit with latent job ID}"
: "${TRANSITION_JOB_ID:?submit with transition job ID}"
: "${PAIR_JOB_ID:?submit with R1 pair job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"; STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
LATENT_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/p1-flat-latents-job-${LATENT_JOB_ID}"
TRANSITION_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/transition-cache-job-${TRANSITION_JOB_ID}"
PAIR_DIR="${STABLEWM_HOME}/derived/acid-alternative-v1/${TASK}/${ARTIFACT_SLUG}/reachability-pairs-job-${PAIR_JOB_ID}"
SEEDS=(6101 6102 6103); if (( SLURM_ARRAY_TASK_ID < 3 )); then CONDITION=true; SEED_INDEX=${SLURM_ARRAY_TASK_ID}; else CONDITION=shuffled_label; SEED_INDEX=$((SLURM_ARRAY_TASK_ID-3)); fi; SEED="${SEEDS[${SEED_INDEX}]}"
OUTPUT="${ROOT}/results/acid-alternative/scorers/${TASK}/reachability/${CONDITION}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-trm-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
for required in "${IMAGE}" "${SOURCE_MANIFEST}" "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" "${TRANSITION_DIR}/transitions.h5" "${TRANSITION_DIR}/manifest.json" "${PAIR_DIR}/pairs.h5" "${PAIR_DIR}/manifest.json"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"; trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"; nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" PYTHONHASHSEED="${SEED}" CUBLAS_WORKSPACE_CONFIG=:4096:8 TMPDIR="${JOB_TMP}" \
  python -m acid_alternative.train_reachability_head --latent-h5 "${LATENT_DIR}/latents.h5" --latent-manifest "${LATENT_DIR}/manifest.json" --pair-h5 "${PAIR_DIR}/pairs.h5" --pair-manifest "${PAIR_DIR}/manifest.json" --transition-h5 "${TRANSITION_DIR}/transitions.h5" --transition-manifest "${TRANSITION_DIR}/manifest.json" --source-manifest "${SOURCE_MANIFEST}" --output-dir "${OUTPUT}" --condition "${CONDITION}" --seed "${SEED}" --device cuda --learning-rate 0.001 --weight-decay 0.0001 --batch-size 1024 --maximum-epochs 200 --patience 20
printf '%s\n' "task=${TASK}" "condition=${CONDITION}" "seed=${SEED}" "array_job_id=${SLURM_ARRAY_JOB_ID}" "array_task_id=${SLURM_ARRAY_TASK_ID}" "node=$(hostname)" > "${OUTPUT}/provenance.txt"
sha256sum "${SOURCE_MANIFEST}" "${OUTPUT}/best.pt" "${OUTPUT}/summary.json" "${OUTPUT}/training.jsonl" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
