#!/usr/bin/env bash
#SBATCH --job-name=gdp-e7p-cache
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e7p-cache-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e7p-cache-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E7P cache snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; TRANSITION_JOB=296629 ;;
  1) TASK=reacher; ARTIFACT=lewm; LATENT_JOB=296647; TRANSITION_JOB=296648 ;;
  2) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; TRANSITION_JOB=296667 ;;
  *) exit 2 ;;
esac
BASE=${ROOT}/data/stablewm/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
TRANSITION=${BASE}/transition-cache-job-${TRANSITION_JOB}
OUT=${BASE}/gdp-cem-sequence-cache-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/build_goal_conditioned_action_sequence_cache.py" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --transition-h5 "${TRANSITION}/transitions.h5" --transition-manifest "${TRANSITION}/manifest.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E7P-SEQUENCE-CACHE-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-h5 "${OUT}/sequences.h5" --output-json "${OUT}/manifest.json"
printf '%s\n' "study=gdp_cem_e7p_sequence_cache" "task=${TASK}" "job_id=${SLURM_JOB_ID}" \
  "d2_read=false" "d3_read=false" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/sequences.h5" "${OUT}/manifest.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"

