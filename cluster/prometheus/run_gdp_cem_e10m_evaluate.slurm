#!/usr/bin/env bash
#SBATCH --job-name=gdp-e10m-p1
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e10m-p1-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e10m-p1-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E10M snapshot}"
: "${E10M_TRAIN_JOB_ID:?missing E10M training array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; CACHE_INDEX=0; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; E7_INDEX=2 ;;
  1) TASK=reacher; ARTIFACT=lewm; LATENT_JOB=296647; CACHE_INDEX=1; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; E7_INDEX=5 ;;
  2) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; CACHE_INDEX=2; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; E7_INDEX=8 ;;
  *) exit 2 ;;
esac
BASE=${ROOT}/data/stablewm/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
SEQUENCE=${BASE}/gdp-cem-sequence-cache-job-297698-${CACHE_INDEX}
E10V_TRAIN_JOB=297778
SEED1_BASE=${ROOT}/results/acid-alternative/gdp-cem-e10v-train/${TASK}
E10M_BASE=${ROOT}/results/acid-alternative/gdp-cem-e10m-train/${TASK}
SEED1_TRUE_INDEX=$((SLURM_ARRAY_TASK_ID * 2))
SEED1_SHUFFLED_INDEX=$((SEED1_TRUE_INDEX + 1))
arguments=(
  --seed1-vp-summary vp_true "${SEED1_BASE}/vp_true/seed-6101-job-${E10V_TRAIN_JOB}-${SEED1_TRUE_INDEX}/summary.json"
  --seed1-vp-summary vp_shuffled_goal "${SEED1_BASE}/vp_shuffled_goal/seed-6101-job-${E10V_TRAIN_JOB}-${SEED1_SHUFFLED_INDEX}/summary.json"
  --seed1-gaussian-summary "${ROOT}/results/acid-alternative/gdp-cem-e7p-proposals/${TASK}/gaussian_true/seed-6101-job-297703-${E7_INDEX}/summary.json"
)
seeds=(6102 6103)
conditions=(vp_true vp_shuffled_goal gaussian_true)
for seed_index in 0 1; do
  seed=${seeds[${seed_index}]}
  for condition_index in 0 1 2; do
    condition=${conditions[${condition_index}]}
    train_index=$((SLURM_ARRAY_TASK_ID * 6 + seed_index * 3 + condition_index))
    arguments+=(--new-summary "${seed}" "${condition}" "${E10M_BASE}/${condition}/seed-${seed}-job-${E10M_TRAIN_JOB_ID}-${train_index}/summary.json")
  done
done
E10V_AGG=${ROOT}/results/acid-alternative/gdp-cem-e10v-p1/analysis/job-297780/summary.json
OUT=${ROOT}/results/acid-alternative/gdp-cem-e10m-p1/${TASK}/job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-gdp-e10m-p1-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${ROOT}/src/hi-lewm:${ROOT}/src/hi-lewm/third_party/lewm" \
  PYTHONHASHSEED=2026081708 CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" \
  SLURM_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e10m_p1.py" \
  --task "${TASK}" --latent-h5 "${LATENT}/latents.h5" \
  --sequence-h5 "${SEQUENCE}/sequences.h5" --sequence-manifest "${SEQUENCE}/manifest.json" \
  --dataset "${ROOT}/data/stablewm/${DATASET}" --world-model-policy "${POLICY}" \
  --world-model-checkpoint "${ROOT}/data/stablewm/${CHECKPOINT}" \
  --stablewm-home "${ROOT}/data/stablewm" "${arguments[@]}" \
  --e10v-aggregate "${E10V_AGG}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E10M-MULTISEED-PURE-VELOCITY-P1-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e10m_p1" "task=${TASK}" "job_id=${SLURM_JOB_ID}" \
  "d2_read=false" "d3_read=false" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/per-context.jsonl" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
