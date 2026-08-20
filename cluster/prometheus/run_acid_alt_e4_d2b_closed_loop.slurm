#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-d2b-closed
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=16:00:00
#SBATCH --array=0-53%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2b-closed-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2b-closed-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4-D2B snapshot path}"
: "${D2A_SNAPSHOT:?submit with immutable E4-D2A snapshot path}"
: "${D2A_ANALYSIS_JOB_ID:?submit with passing E4-D2A analysis job ID}"
: "${PREFLIGHT_JOB_ID:?submit with passing E4-D2B preflight job ID}"
: "${CONTROLS_JOB_ID:?submit with completed inverse-controls job ID}"
: "${P1_TRAIN_JOB_ID:?submit with completed E4-P1 training job ID}"
: "${MANIFEST_JOB_ID:?submit with frozen D2 manifest job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM_HOME=${ROOT}/data/stablewm
PLANNER_SEED=8401
task_index=$((SLURM_ARRAY_TASK_ID / 18))
arm_index=$((SLURM_ARRAY_TASK_ID % 18))
case "${task_index}" in
  0) TASK=pusht; DATASET_NAME=pusht_expert_train; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; SCORER_JOB=296631; REACH_JOB=296633; E4_TRUE=0; E4_SHUFFLED=1; CONTROL_BASE=0 ;;
  1) TASK=reacher; DATASET_NAME=dmc/reacher_random; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; SCORER_JOB=296650; REACH_JOB=296652; E4_TRUE=2; E4_SHUFFLED=3; CONTROL_BASE=2 ;;
  2) TASK=cube; DATASET_NAME=ogbench/cube_single_expert; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; SCORER_JOB=296669; REACH_JOB=296671; E4_TRUE=4; E4_SHUFFLED=5; CONTROL_BASE=4 ;;
  *) exit 2 ;;
esac
ARMS=(
  b0 acid_l002 acid acid_l014 acid_flow acid_16_mean acid_16_min
  forward reachability deterministic_inverse gaussian_tail
  cider_tail_l002 cider_tail cider_tail_l014 cider_shuffled dide
  cider_raw cider_mean_violation
)
ARM=${ARMS[${arm_index}]}
artifact_arguments=()
case "${ARM}" in
  b0) ;;
  acid_l002|acid|acid_l014|acid_flow|acid_16_mean|acid_16_min)
    artifact_arguments+=(--scorer-artifact "${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-6101-job-${SCORER_JOB}-0/best.pt")
    ;;
  forward)
    artifact_arguments+=(--scorer-artifact "${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-6101-job-${SCORER_JOB}-6/best.pt")
    ;;
  reachability)
    artifact_arguments+=(--scorer-artifact "${ROOT}/results/acid-alternative/scorers/${TASK}/reachability/true/seed-6101-job-${REACH_JOB}-0/best.pt")
    ;;
  deterministic_inverse)
    artifact_arguments+=(--scorer-artifact "${ROOT}/results/acid-alternative/e4-d2a/controls/${TASK}/deterministic/seed-7101-job-${CONTROLS_JOB_ID}-${CONTROL_BASE}/summary.json")
    ;;
  gaussian_tail)
    artifact_arguments+=(--scorer-artifact "${ROOT}/results/acid-alternative/e4-d2a/controls/${TASK}/gaussian/seed-7101-job-${CONTROLS_JOB_ID}-$((CONTROL_BASE + 1))/summary.json")
    ;;
  cider_shuffled)
    artifact_arguments+=(--scorer-artifact "${ROOT}/results/acid-alternative/e4-p1/${TASK}/shuffled_successor/seed-7101-job-${P1_TRAIN_JOB_ID}-${E4_SHUFFLED}/summary.json")
    ;;
  cider_tail_l002|cider_tail|cider_tail_l014|dide|cider_raw|cider_mean_violation)
    artifact_arguments+=(--scorer-artifact "${ROOT}/results/acid-alternative/e4-p1/${TASK}/true_successor/seed-7101-job-${P1_TRAIN_JOB_ID}-${E4_TRUE}/summary.json")
    ;;
  *) exit 2 ;;
esac
MANIFEST_DIR=${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-${MANIFEST_JOB_ID}
D2A_ANALYSIS_DIR=${ROOT}/results/acid-alternative/e4-d2a/analysis/job-${D2A_ANALYSIS_JOB_ID}
OUT=${ROOT}/results/acid-alternative/e4-d2b/closed-loop/${TASK}/${ARM}/planner-seed-${PLANNER_SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-e4-d2b-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test -f "${D2A_ANALYSIS_DIR}/e4-d2b-authorization.json"
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
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_acid_alt_e4_d2b.py" \
  --task "${TASK}" --arm "${ARM}" --planner-seed "${PLANNER_SEED}" \
  --parent-protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md" \
  --d2b-freeze "${SNAPSHOT}/ACID-ALTERNATIVE-E4-D2B-CLOSED-LOOP-FREEZE-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --d2a-implementation-freeze "${D2A_SNAPSHOT}/ACID-ALTERNATIVE-E4-D2A-IMPLEMENTATION-FREEZE-2026-08-16.md" \
  --d2a-source-manifest "${D2A_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --d2a-analysis "${D2A_ANALYSIS_DIR}/summary.json" \
  --d2a-authorization "${D2A_ANALYSIS_DIR}/e4-d2b-authorization.json" \
  --code-root "${CODE}" --stablewm-home "${STABLEWM_HOME}" \
  --dataset "${STABLEWM_HOME}/${DATASET}" --dataset-name "${DATASET_NAME}" \
  --world-model-policy "${POLICY}" --world-model-checkpoint "${STABLEWM_HOME}/${CHECKPOINT}" \
  --eval-manifest "${MANIFEST_DIR}/d2-fresh.tsv" --eval-provenance "${MANIFEST_DIR}/provenance.json" \
  "${artifact_arguments[@]}" --output-dir "${OUT}"
printf '%s\n' \
  "study=e4_d2b_exploratory_closed_loop" "task=${TASK}" "arm=${ARM}" \
  "planner_seed=${PLANNER_SEED}" "job_id=${SLURM_JOB_ID}" \
  "d2a_analysis_job_id=${D2A_ANALYSIS_JOB_ID}" "preflight_job_id=${PREFLIGHT_JOB_ID}" \
  "confirmation_claim_allowed=false" "alternative_to_acid_claim_allowed=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/summary.json" "${OUT}/episodes.tsv" "${OUT}/cem-diagnostics.jsonl" \
  "${OUT}/resolved-config.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"

