#!/usr/bin/env bash
#SBATCH --job-name=gdp-e12-head
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --array=0-17%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-head-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-head-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E12 Stage-B snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
task_index=$((SLURM_ARRAY_TASK_ID / 6))
within_task=$((SLURM_ARRAY_TASK_ID % 6))
seed_index=$((within_task / 2))
mode_index=$((within_task % 2))
case "${task_index}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; CACHE_INDEX=0 ;;
  1) TASK=reacher; ARTIFACT=lewm; LATENT_JOB=296647; CACHE_INDEX=1 ;;
  2) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; CACHE_INDEX=2 ;;
  *) exit 2 ;;
esac
SEEDS=(6101 6102 6103)
MODES=(h25 endframe)
SEED=${SEEDS[${seed_index}]}
GOAL_MODE=${MODES[${mode_index}]}
BASE=${ROOT}/data/stablewm/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
SEQUENCE=${BASE}/gdp-cem-sequence-cache-job-297698-${CACHE_INDEX}
OUT=${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b/${TASK}/seed-${SEED}/prism-head-${GOAL_MODE}
JOB_TMP=/tmp/ckontzias-gdp-e12-head-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT%/*}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  PYTHONHASHSEED="${SEED}" CUBLAS_WORKSPACE_CONFIG=:4096:8 HDF5_USE_FILE_LOCKING=FALSE \
  TMPDIR="${JOB_TMP}" SLURM_JOB_ID="${SLURM_JOB_ID}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/train_gdp_cem_e12_prism_head.py" \
  --task "${TASK}" --goal-mode "${GOAL_MODE}" --seed "${SEED}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --latent-h5 "${LATENT}/latents.h5" --latent-manifest "${LATENT}/manifest.json" \
  --sequence-h5 "${SEQUENCE}/sequences.h5" --sequence-manifest "${SEQUENCE}/manifest.json" \
  --output-dir "${OUT}"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"] == "ok"' "${OUT}/summary.json"
printf '%s\n' "study=gdp_cem_e12_stage_b" "method=prism_head" "task=${TASK}" \
  "goal_mode=${GOAL_MODE}" "seed=${SEED}" "job_id=${SLURM_JOB_ID}" \
  "d3_read=false" "d4_read=false" "protected_p4_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/best.pt" "${OUT}/training.jsonl" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
