#!/usr/bin/env bash
#SBATCH --job-name=gdp-e13-smoke
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --nodelist=gpu09
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --array=0-14%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-smoke-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e13-smoke-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E13 snapshot}"
: "${PREFLIGHT_JOB_ID:?missing E13 preflight job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM_HOME=${ROOT}/data/stablewm
task_index=$((SLURM_ARRAY_TASK_ID / 5))
arm_index=$((SLURM_ARRAY_TASK_ID % 5))
case "${task_index}" in
  0) TASK=pusht; DATASET_NAME=pusht_expert_train; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; VP_INDEX=0; GAUSSIAN_INDEX=2 ;;
  1) TASK=reacher; DATASET_NAME=dmc/reacher_random; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; VP_INDEX=2; GAUSSIAN_INDEX=5 ;;
  2) TASK=cube; DATASET_NAME=ogbench/cube_single_expert; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; VP_INDEX=4; GAUSSIAN_INDEX=8 ;;
  *) exit 2 ;;
esac
ARMS=(latent_gaussian_select_k300 vp_select_k300 prism_dp_select_k300 vp_select_k16 prism_dp_select_k16)
ARM=${ARMS[${arm_index}]}
case "${ARM}" in
  latent_gaussian_select_k300) SUMMARY=${ROOT}/results/acid-alternative/gdp-cem-e7p-proposals/${TASK}/gaussian_true/seed-6101-job-297703-${GAUSSIAN_INDEX}/summary.json ;;
  *) SUMMARY=${ROOT}/results/acid-alternative/gdp-cem-e10v-train/${TASK}/vp_true/seed-6101-job-297778-${VP_INDEX}/summary.json ;;
esac
MANIFEST_DIR=${ROOT}/results/acid-alternative/gdp-cem-e13/preflight/job-${PREFLIGHT_JOB_ID}/p1-smoke-manifests/${TASK}
OUT=${ROOT}/results/acid-alternative/gdp-cem-e13/p1-smoke/${TASK}/${ARM}/job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-gdp-e13-smoke-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
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
  --mode p1_smoke --task "${TASK}" --arm "${ARM}" --model-seed 6101 --shard 0 \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --e12-stage-b-audit "${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b/STAGE-B-AUDIT.json" \
  --e12-training-source-manifest "${ROOT}/snapshots/gdp-cem-e12-stage-b-e2faf062f3eec188/SOURCE-MANIFEST.sha256" \
  --e10m-aggregate "${ROOT}/results/acid-alternative/gdp-cem-e10m-p1/analysis/job-297790/summary.json" \
  --code-root "${CODE}" --stablewm-home "${STABLEWM_HOME}" \
  --dataset "${STABLEWM_HOME}/${DATASET}" --dataset-name "${DATASET_NAME}" \
  --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM_HOME}/${CHECKPOINT}" \
  --eval-manifest "${MANIFEST_DIR}/p1-smoke.tsv" \
  --eval-provenance "${MANIFEST_DIR}/provenance.json" \
  --proposal-summary "${SUMMARY}" --output-dir "${OUT}"
python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"] == "ok" and x["mode"] == "p1_smoke" and x["d4_read"] is False' "${OUT}/summary.json"
printf '%s\n' "study=gdp_cem_e13_p1_smoke" "task=${TASK}" "arm=${ARM}" \
  'model_seed=6101' 'd4_read=false' 'claim_allowed=false' > "${OUT}/audit.txt"
(cd "${OUT}" && sha256sum summary.json episodes.tsv resolved-config.json \
  solver-diagnostics.jsonl proposal-diagnostics.jsonl audit.txt > sha256.txt)
chmod a-w "${OUT}"/* "${OUT}"
