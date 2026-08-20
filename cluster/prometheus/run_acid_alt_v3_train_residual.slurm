#!/usr/bin/env bash
#SBATCH --job-name=acid-v3-residual
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --array=0-11%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-residual-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-residual-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable v3 snapshot path}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
task_index=$((SLURM_ARRAY_TASK_ID / 4))
within=$((SLURM_ARRAY_TASK_ID % 4))
case "${task_index}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; TRANSITION_JOB=296629; SCORER_JOB=296631 ;;
  1) TASK=reacher; ARTIFACT=lewm; LATENT_JOB=296647; TRANSITION_JOB=296648; SCORER_JOB=296650 ;;
  2) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; TRANSITION_JOB=296667; SCORER_JOB=296669 ;;
  *) exit 2 ;;
esac
if (( within < 2 )); then CONDITION=true; else CONDITION=shuffled_action; fi
SEED=$((6102 + (within % 2)))
diffusion_index=$((SEED - 6098))
forward_index=$((SEED - 6095))
BASE=${ROOT}/data/stablewm/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
OUT=${ROOT}/results/acid-alternative/scorers-v3-d2/${TASK}/${CONDITION}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-v3-train-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED="${SEED}" \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/train_residual_diffusion_multiseed_20260816.py" \
  --base-trainer-source "${SNAPSHOT}/train_residual_diffusion_pilot_20260816.py" \
  --condition "${CONDITION}" \
  --latent-h5 "${BASE}/p1-flat-latents-job-${LATENT_JOB}/latents.h5" \
  --latent-manifest "${BASE}/p1-flat-latents-job-${LATENT_JOB}/manifest.json" \
  --transition-h5 "${BASE}/transition-cache-job-${TRANSITION_JOB}/transitions.h5" \
  --transition-manifest "${BASE}/transition-cache-job-${TRANSITION_JOB}/manifest.json" \
  --v1-diffusion-checkpoint "${ROOT}/results/acid-alternative/scorers/${TASK}/diffusion/true/seed-${SEED}-job-${SCORER_JOB}-${diffusion_index}/best.pt" \
  --forward-checkpoint "${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-${SEED}-job-${SCORER_JOB}-${forward_index}/best.pt" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUT}" --seed "${SEED}"
printf '%s\n' "task=${TASK}" "condition=${CONDITION}" "seed=${SEED}" "job_id=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/best.pt" "${OUT}/validation-examples.npz" "${OUT}/training.jsonl" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
