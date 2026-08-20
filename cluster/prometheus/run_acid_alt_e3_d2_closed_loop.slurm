#!/usr/bin/env bash
#SBATCH --job-name=acid-e3-d2-closed
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=16:00:00
#SBATCH --array=0-53%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e3-d2-closed-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e3-d2-closed-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E3 snapshot path}"
: "${TRAIN_JOB_ID:?submit with residual training array ID}"
: "${MANIFEST_JOB_ID:?submit with D2 manifest job ID}"
: "${AUTH_JOB_ID:?submit with completed E3 authorization job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM_HOME=${ROOT}/data/stablewm
task_index=$((SLURM_ARRAY_TASK_ID / 18))
within=$((SLURM_ARRAY_TASK_ID % 18))
arm_index=$((within / 3))
seed_offset=$((within % 3))
case "${task_index}" in
  0) TASK=pusht; DATASET_NAME=pusht_expert_train; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; SCORER_JOB=296631; OLD_TRUE=0; OLD_SHUFFLED=1; TRAIN_BASE=0 ;;
  1) TASK=reacher; DATASET_NAME=dmc/reacher_random; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; SCORER_JOB=296650; OLD_TRUE=2; OLD_SHUFFLED=3; TRAIN_BASE=4 ;;
  2) TASK=cube; DATASET_NAME=ogbench/cube_single_expert; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; SCORER_JOB=296669; OLD_TRUE=4; OLD_SHUFFLED=5; TRAIN_BASE=8 ;;
  *) exit 2 ;;
esac
ARMS=(b0 acid forward rdx ae ae_shuffled)
ARM=${ARMS[${arm_index}]}
SCORER_SEED=$((6101 + seed_offset))
PLANNER_SEED=$((8301 + seed_offset))
scorer_arguments=()
case "${ARM}" in
  b0) ;;
  acid)
    scorer_arguments+=(--scorer-checkpoint "${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-${SCORER_SEED}-job-${SCORER_JOB}-${seed_offset}/best.pt")
    ;;
  forward)
    forward_index=$((seed_offset + 6))
    scorer_arguments+=(--scorer-checkpoint "${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-${SCORER_SEED}-job-${SCORER_JOB}-${forward_index}/best.pt")
    ;;
  rdx|ae)
    if (( SCORER_SEED == 6101 )); then
      summary=${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${TASK}/true/seed-6101-job-297483-${OLD_TRUE}/summary.json
    else
      train_index=$((TRAIN_BASE + SCORER_SEED - 6102))
      summary=${ROOT}/results/acid-alternative/scorers-v3-d2/${TASK}/true/seed-${SCORER_SEED}-job-${TRAIN_JOB_ID}-${train_index}/summary.json
    fi
    scorer_arguments+=(--scorer-summary "${summary}")
    ;;
  ae_shuffled)
    if (( SCORER_SEED == 6101 )); then
      summary=${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${TASK}/shuffled_action/seed-6101-job-297483-${OLD_SHUFFLED}/summary.json
    else
      train_index=$((TRAIN_BASE + 2 + SCORER_SEED - 6102))
      summary=${ROOT}/results/acid-alternative/scorers-v3-d2/${TASK}/shuffled_action/seed-${SCORER_SEED}-job-${TRAIN_JOB_ID}-${train_index}/summary.json
    fi
    scorer_arguments+=(--scorer-summary "${summary}")
    ;;
esac
MANIFEST_DIR=${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-${MANIFEST_JOB_ID}
AUTH_DIR=${ROOT}/results/acid-alternative/e3-d2-exploratory/authorization/job-${AUTH_JOB_ID}
OUT=${ROOT}/results/acid-alternative/e3-d2-exploratory/closed-loop/${TASK}/${ARM}/scorer-seed-${SCORER_SEED}-planner-seed-${PLANNER_SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-e3-d2-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test -f "${AUTH_DIR}/authorization.json"
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED="${PLANNER_SEED}" CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  SLURM_JOB_ID="${SLURM_JOB_ID}" SLURM_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_acid_alt_e3_d2.py" \
  --task "${TASK}" --arm "${ARM}" --scorer-seed "${SCORER_SEED}" --planner-seed "${PLANNER_SEED}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --exploratory-authorization "${AUTH_DIR}/authorization.json" \
  --trainer-source "${SNAPSHOT}/train_residual_diffusion_pilot_20260816.py" \
  --code-root "${CODE}" --stablewm-home "${STABLEWM_HOME}" --dataset "${STABLEWM_HOME}/${DATASET}" \
  --dataset-name "${DATASET_NAME}" --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM_HOME}/${CHECKPOINT}" \
  --eval-manifest "${MANIFEST_DIR}/d2-fresh.tsv" --eval-provenance "${MANIFEST_DIR}/provenance.json" \
  "${scorer_arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "study=e3_exploratory_d2_closed_loop" "task=${TASK}" "arm=${ARM}" "scorer_seed=${SCORER_SEED}" "planner_seed=${PLANNER_SEED}" "job_id=${SLURM_JOB_ID}" "v3_stage_b_authorized=false" "confirmation_claim_allowed=false" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/episodes.tsv" "${OUT}/cem-diagnostics.jsonl" "${OUT}/resolved-config.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"


