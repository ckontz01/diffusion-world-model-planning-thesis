#!/usr/bin/env bash
#SBATCH --job-name=acid-v3-capture
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-capture-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-capture-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable v3 snapshot path}"
: "${MANIFEST_JOB_ID:?submit with D2 manifest job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM_HOME=${ROOT}/data/stablewm
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; DATASET_NAME=pusht_expert_train; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt ;;
  1) TASK=reacher; DATASET_NAME=dmc/reacher_random; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt ;;
  2) TASK=cube; DATASET_NAME=ogbench/cube_single_expert; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt ;;
  *) exit 2 ;;
esac
MANIFEST=${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-${MANIFEST_JOB_ID}/d2-fresh.tsv
OUT=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/capture/planner-seed-8201-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-v3-capture-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=8201 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" -m acid_alternative_diagnostics.capture_candidate_pools \
  --code-root "${CODE}" --eval-config-name "${TASK}" --stablewm-home "${STABLEWM_HOME}" \
  --dataset "${STABLEWM_HOME}/${DATASET}" --dataset-name "${DATASET_NAME}" \
  --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM_HOME}/${CHECKPOINT}" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --eval-manifest "${MANIFEST}" \
  --analysis-role D2 --planner-seed 8201 --goal-offset 25 --horizon 5 --receding-horizon 5 --action-block 5 \
  --cem-samples 300 --cem-steps 30 --cem-topk 30 --output-dir "${OUT}"
printf '%s\n' "task=${TASK}" "analysis_role=D2" "planner_seed=8201" "job_id=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/candidate-pools.pt" "${OUT}/manifest.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
