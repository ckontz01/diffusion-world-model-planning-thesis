#!/usr/bin/env bash
#SBATCH --job-name=gdp-e10m-tr
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --array=0-17%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e10m-tr-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e10m-tr-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E10M snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
task_index=$((SLURM_ARRAY_TASK_ID / 6))
within_task=$((SLURM_ARRAY_TASK_ID % 6))
seed_index=$((within_task / 3))
condition_index=$((within_task % 3))
case "${task_index}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; CACHE_INDEX=0; CACHE_MANIFEST_SHA=b98c17f107cbfd5daca8d387d83e034460ff8f2535113a3c05467f68442ef9cb ;;
  1) TASK=reacher; ARTIFACT=lewm; LATENT_JOB=296647; CACHE_INDEX=1; CACHE_MANIFEST_SHA=e0e202cd5da1d057b0cb6ba423eae1971f15dd38a871ad581c4f683c8eec9479 ;;
  2) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; CACHE_INDEX=2; CACHE_MANIFEST_SHA=dede8e8d6941008fbb7c910fa2f07666e8e77c93924c007e244f1a890790a80b ;;
  *) exit 2 ;;
esac
seeds=(6102 6103)
conditions=(vp_true vp_shuffled_goal gaussian_true)
SEED=${seeds[${seed_index}]}
CONDITION=${conditions[${condition_index}]}
BASE=${ROOT}/data/stablewm/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
SEQUENCE=${BASE}/gdp-cem-sequence-cache-job-297698-${CACHE_INDEX}
OUT=${ROOT}/results/acid-alternative/gdp-cem-e10m-train/${TASK}/${CONDITION}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-gdp-e10m-tr-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  PYTHONHASHSEED="${SEED}" CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" \
  SLURM_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/train_gdp_cem_e10m_models.py" \
  --task "${TASK}" --condition "${CONDITION}" --seed "${SEED}" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --sequence-h5 "${SEQUENCE}/sequences.h5" --sequence-manifest "${SEQUENCE}/manifest.json" \
  --expected-sequence-manifest-sha256 "${CACHE_MANIFEST_SHA}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E10M-MULTISEED-PURE-VELOCITY-P1-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e10m_train" "task=${TASK}" "condition=${CONDITION}" \
  "seed=${SEED}" "job_id=${SLURM_JOB_ID}" "d2_read=false" "d3_read=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/best.pt" "${OUT}/training.jsonl" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
