#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-p1
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --array=0-5%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-p1-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-p1-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4 snapshot path}"
: "${PREFLIGHT_JOB_ID:?submit with the completed E4 preflight job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
task_index=$((SLURM_ARRAY_TASK_ID / 2))
condition_index=$((SLURM_ARRAY_TASK_ID % 2))
case "${task_index}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; TRANSITION_JOB=296629; SCORER_JOB=296631 ;;
  1) TASK=reacher; ARTIFACT=lewm; LATENT_JOB=296647; TRANSITION_JOB=296648; SCORER_JOB=296650 ;;
  2) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; TRANSITION_JOB=296667; SCORER_JOB=296669 ;;
  *) exit 2 ;;
esac
case "${condition_index}" in
  0) CONDITION=true_successor ;;
  1) CONDITION=shuffled_successor ;;
  *) exit 2 ;;
esac
SEED=7101
BASE=${ROOT}/data/stablewm/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
ACID=${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-6101-job-${SCORER_JOB}-0/best.pt
OUT=${ROOT}/results/acid-alternative/e4-p1/${TASK}/${CONDITION}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-e4-p1-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" /usr/bin/env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED="${SEED}" \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/train_acid_alt_e4_didm.py" \
  --task "${TASK}" --condition "${CONDITION}" \
  --latent-h5 "${BASE}/p1-flat-latents-job-${LATENT_JOB}/latents.h5" \
  --latent-manifest "${BASE}/p1-flat-latents-job-${LATENT_JOB}/manifest.json" \
  --transition-h5 "${BASE}/transition-cache-job-${TRANSITION_JOB}/transitions.h5" \
  --transition-manifest "${BASE}/transition-cache-job-${TRANSITION_JOB}/manifest.json" \
  --acid-checkpoint "${ACID}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUT}" --seed "${SEED}"
printf '%s\n' \
  "task=${TASK}" \
  "condition=${CONDITION}" \
  "seed=${SEED}" \
  "job_id=${SLURM_JOB_ID}" \
  "preflight_job_id=${PREFLIGHT_JOB_ID}" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/summary.json" \
  "${OUT}/best.pt" \
  "${OUT}/calibration.json" \
  "${OUT}/validation-examples.npz" \
  "${OUT}/training.jsonl" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
