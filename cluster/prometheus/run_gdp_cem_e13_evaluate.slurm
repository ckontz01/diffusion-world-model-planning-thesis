#!/usr/bin/env bash
#SBATCH --job-name=gdp-e13-d4
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --nodelist=gpu09
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --array=0-359%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-d4-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-d4-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E13 snapshot}"
: "${MANIFEST_JOB_ID:?missing E13 D4 manifest array}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM_HOME=${ROOT}/data/stablewm

per_task=$((3 * 5 * 8))
per_seed=$((5 * 8))
task_index=$((SLURM_ARRAY_TASK_ID / per_task))
within_task=$((SLURM_ARRAY_TASK_ID % per_task))
seed_index=$((within_task / per_seed))
within_seed=$((within_task % per_seed))
arm_index=$((within_seed / 8))
shard=$((within_seed % 8))
case "${task_index}" in
  0) TASK=pusht; DATASET_NAME=pusht_expert_train; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; E10V_TRUE=0; E7_GAUSSIAN=2; E10M_BASE=0 ;;
  1) TASK=reacher; DATASET_NAME=dmc/reacher_random; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; E10V_TRUE=2; E7_GAUSSIAN=5; E10M_BASE=6 ;;
  2) TASK=cube; DATASET_NAME=ogbench/cube_single_expert; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; E10V_TRUE=4; E7_GAUSSIAN=8; E10M_BASE=12 ;;
  *) exit 2 ;;
esac
SEEDS=(6101 6102 6103)
ARMS=(latent_gaussian_select_k300 vp_select_k300 prism_dp_select_k300 vp_select_k16 prism_dp_select_k16)
MODEL_SEED=${SEEDS[${seed_index}]}
ARM=${ARMS[${arm_index}]}
case "${ARM}" in
  latent_gaussian_select_k300) CONDITION=gaussian_true; CONDITION_INDEX=2 ;;
  *) CONDITION=vp_true; CONDITION_INDEX=0 ;;
esac
if (( MODEL_SEED == 6101 )); then
  if [[ "${CONDITION}" == gaussian_true ]]; then
    SUMMARY=${ROOT}/results/acid-alternative/gdp-cem-e7p-proposals/${TASK}/gaussian_true/seed-6101-job-297703-${E7_GAUSSIAN}/summary.json
  else
    SUMMARY=${ROOT}/results/acid-alternative/gdp-cem-e10v-train/${TASK}/vp_true/seed-6101-job-297778-${E10V_TRUE}/summary.json
  fi
else
  E10M_INDEX=$((E10M_BASE + (MODEL_SEED - 6102) * 3 + CONDITION_INDEX))
  SUMMARY=${ROOT}/results/acid-alternative/gdp-cem-e10m-train/${TASK}/${CONDITION}/seed-${MODEL_SEED}-job-297788-${E10M_INDEX}/summary.json
fi

MANIFEST_DIR=${ROOT}/manifests/gdp-cem-e13-d4/${TASK}/job-${MANIFEST_JOB_ID}
OUT=${ROOT}/results/acid-alternative/gdp-cem-e13-d4/closed-loop/${TASK}/${ARM}/model-seed-${MODEL_SEED}/shard-${shard}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-gdp-e13-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
  SDL_VIDEODRIVER=dummy MPLBACKEND=Agg SLURM_JOB_ID="${SLURM_JOB_ID}" \
  SLURM_ARRAY_JOB_ID="${SLURM_ARRAY_JOB_ID}" SLURM_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID}" \
  TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e13_d4.py" \
  --mode d4 --task "${TASK}" --arm "${ARM}" --model-seed "${MODEL_SEED}" --shard "${shard}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --e12-stage-b-audit "${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b/STAGE-B-AUDIT.json" \
  --e12-training-source-manifest "${ROOT}/snapshots/gdp-cem-e12-stage-b-e2faf062f3eec188/SOURCE-MANIFEST.sha256" \
  --e10m-aggregate "${ROOT}/results/acid-alternative/gdp-cem-e10m-p1/analysis/job-297790/summary.json" \
  --code-root "${CODE}" --stablewm-home "${STABLEWM_HOME}" \
  --dataset "${STABLEWM_HOME}/${DATASET}" --dataset-name "${DATASET_NAME}" \
  --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM_HOME}/${CHECKPOINT}" \
  --eval-manifest "${MANIFEST_DIR}/d4-untouched.tsv" \
  --eval-provenance "${MANIFEST_DIR}/provenance.json" \
  --proposal-summary "${SUMMARY}" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e13_d4" "task=${TASK}" "arm=${ARM}" \
  "model_seed=${MODEL_SEED}" "shard=${shard}" "job_id=${SLURM_ARRAY_JOB_ID}" \
  "array_task_id=${SLURM_ARRAY_TASK_ID}" 'd4_read=true' \
  'partial_metrics_inspected=false' 'protected_p4_c1_i1_read=false' \
  > "${OUT}/audit.txt"
(cd "${OUT}" && sha256sum summary.json episodes.tsv resolved-config.json \
  solver-diagnostics.jsonl proposal-diagnostics.jsonl audit.txt > sha256.txt)
chmod a-w "${OUT}"/* "${OUT}"
