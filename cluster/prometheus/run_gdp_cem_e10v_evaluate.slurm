#!/usr/bin/env bash
#SBATCH --job-name=gdp-e10v-p1
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e10v-p1-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e10v-p1-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E10V snapshot}"
: "${E10V_TRAIN_JOB_ID:?missing E10V training array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; ARTIFACT=lewm-hf-22b330c; LATENT_JOB=296628; CACHE_INDEX=0; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; E7_BASE=0 ;;
  1) TASK=reacher; ARTIFACT=lewm; LATENT_JOB=296647; CACHE_INDEX=1; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; E7_BASE=3 ;;
  2) TASK=cube; ARTIFACT=lewm-hf-b0747c5; LATENT_JOB=296666; CACHE_INDEX=2; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; E7_BASE=6 ;;
  *) exit 2 ;;
esac
BASE=${ROOT}/data/stablewm/derived/acid-alternative-v1/${TASK}/${ARTIFACT}
LATENT=${BASE}/p1-flat-latents-job-${LATENT_JOB}
SEQUENCE=${BASE}/gdp-cem-sequence-cache-job-297698-${CACHE_INDEX}
VP_TRUE_INDEX=$((SLURM_ARRAY_TASK_ID * 2))
VP_SHUFFLED_INDEX=$((VP_TRUE_INDEX + 1))
VP_ROOT=${ROOT}/results/acid-alternative/gdp-cem-e10v-train/${TASK}
E7_ROOT=${ROOT}/results/acid-alternative/gdp-cem-e7p-proposals/${TASK}
OUT=${ROOT}/results/acid-alternative/gdp-cem-e10v-p1/${TASK}/job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-gdp-e10v-p1-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
vp_arguments=(
  --vp-summary vp_true "${VP_ROOT}/vp_true/seed-6101-job-${E10V_TRAIN_JOB_ID}-${VP_TRUE_INDEX}/summary.json"
  --vp-summary vp_shuffled_goal "${VP_ROOT}/vp_shuffled_goal/seed-6101-job-${E10V_TRAIN_JOB_ID}-${VP_SHUFFLED_INDEX}/summary.json"
)
e7_conditions=(diffusion_true diffusion_shuffled_goal gaussian_true)
e7_arguments=()
for offset in 0 1 2; do
  condition=${e7_conditions[${offset}]}
  index=$((E7_BASE + offset))
  e7_arguments+=(--e7-summary "${condition}" "${E7_ROOT}/${condition}/seed-6101-job-297703-${index}/summary.json")
done
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${ROOT}/src/hi-lewm:${ROOT}/src/hi-lewm/third_party/lewm" \
  PYTHONHASHSEED=2026081707 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
  SLURM_JOB_ID="${SLURM_JOB_ID}" SLURM_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e10v_p1.py" \
  --task "${TASK}" --latent-h5 "${LATENT}/latents.h5" \
  --sequence-h5 "${SEQUENCE}/sequences.h5" --sequence-manifest "${SEQUENCE}/manifest.json" \
  --dataset "${ROOT}/data/stablewm/${DATASET}" --world-model-policy "${POLICY}" \
  --world-model-checkpoint "${ROOT}/data/stablewm/${CHECKPOINT}" \
  --stablewm-home "${ROOT}/data/stablewm" "${vp_arguments[@]}" "${e7_arguments[@]}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E10V-PURE-VELOCITY-DIFFUSION-P1-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e10v_p1" "task=${TASK}" "job_id=${SLURM_JOB_ID}" \
  "d2_read=false" "d3_read=false" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/per-context.jsonl" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
