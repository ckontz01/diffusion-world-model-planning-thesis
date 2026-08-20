#!/usr/bin/env bash
#SBATCH --job-name=acid-e6-d2
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --array=0-29%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6-d2-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6-d2-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E6 snapshot path}"
: "${AUTH_JOB_ID:?submit with completed E6 authorization job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM_HOME=${ROOT}/data/stablewm
MANIFEST_JOB_ID=297535
SCORER_SEED=6101
PLANNER_SEED=8301

task_index=$((SLURM_ARRAY_TASK_ID / 10))
arm_index=$((SLURM_ARRAY_TASK_ID % 10))
case "${task_index}" in
  0) TASK=pusht; DATASET_NAME=pusht_expert_train; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; SCORER_JOB=296631; TRUE_INDEX=0; SHUFFLED_INDEX=1 ;;
  1) TASK=reacher; DATASET_NAME=dmc/reacher_random; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; SCORER_JOB=296650; TRUE_INDEX=2; SHUFFLED_INDEX=3 ;;
  2) TASK=cube; DATASET_NAME=ogbench/cube_single_expert; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; SCORER_JOB=296669; TRUE_INDEX=4; SHUFFLED_INDEX=5 ;;
  *) exit 2 ;;
esac
ARMS=(
  b0
  acid_cont
  forward_cont
  rdx_cont
  rdx_gate_tail5_q20
  rdx_gate_tail5_q40
  rdx_gate_all_q40
  rdx_shuffled_gate_tail5_q40
  acid_gate_tail5_q40
  forward_gate_tail5_q40
)
ARM=${ARMS[${arm_index}]}
scorer_arguments=()
case "${ARM}" in
  b0) ;;
  acid_cont|acid_gate_tail5_q40)
    scorer_arguments+=(--scorer-checkpoint "${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-6101-job-${SCORER_JOB}-0/best.pt")
    ;;
  forward_cont|forward_gate_tail5_q40)
    scorer_arguments+=(--scorer-checkpoint "${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-6101-job-${SCORER_JOB}-6/best.pt")
    ;;
  rdx_shuffled_gate_tail5_q40)
    scorer_arguments+=(--scorer-summary "${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${TASK}/shuffled_action/seed-6101-job-297483-${SHUFFLED_INDEX}/summary.json")
    ;;
  rdx_cont|rdx_gate_tail5_q20|rdx_gate_tail5_q40|rdx_gate_all_q40)
    scorer_arguments+=(--scorer-summary "${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${TASK}/true/seed-6101-job-297483-${TRUE_INDEX}/summary.json")
    ;;
  *) exit 2 ;;
esac

MANIFEST_DIR=${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-${MANIFEST_JOB_ID}
AUTH=${ROOT}/results/acid-alternative/e6-d2-quantile/authorization/job-${AUTH_JOB_ID}/authorization.json
OUT=${ROOT}/results/acid-alternative/e6-d2-quantile/closed-loop/${TASK}/${ARM}/seed-6101-8301-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-e6-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test -f "${AUTH}"
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=8301 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  SLURM_JOB_ID="${SLURM_JOB_ID}" SLURM_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_acid_alt_e6_d2.py" \
  --task "${TASK}" --arm "${ARM}" --scorer-seed 6101 --planner-seed 8301 \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E6-QUANTILE-CONSTRAINED-CEM-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --authorization "${AUTH}" \
  --trainer-source "${SNAPSHOT}/train_residual_diffusion_pilot_20260816.py" \
  --code-root "${CODE}" --stablewm-home "${STABLEWM_HOME}" --dataset "${STABLEWM_HOME}/${DATASET}" \
  --dataset-name "${DATASET_NAME}" --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM_HOME}/${CHECKPOINT}" \
  --eval-manifest "${MANIFEST_DIR}/d2-fresh.tsv" --eval-provenance "${MANIFEST_DIR}/provenance.json" \
  "${scorer_arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "study=e6_exposed_d2_quantile" "task=${TASK}" "arm=${ARM}" "job_id=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/episodes.tsv" "${OUT}/cem-diagnostics.jsonl" "${OUT}/resolved-config.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
