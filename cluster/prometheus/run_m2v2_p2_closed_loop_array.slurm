#!/usr/bin/env bash

# PushT and TwoRoom x five frozen weights x twelve frozen P2 queries.

#SBATCH --job-name=m2v2-p2-grid
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --array=0-119%3
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/m2v2-p2-grid-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/m2v2-p2-grid-%A_%a.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
SCRIPT="${ROOT}/scripts/run_m2v2_p2_closed_loop_query.py"
SCORER="${ROOT}/scripts/m2v2_likelihood_ratio.py"
CORE_RUNNER="${ROOT}/scripts/run_p2_augmented_closed_loop_query.py"
CORE_WRAPPER="${ROOT}/scripts/feasibility_augmented_high_cost.py"
RUNNER="${ROOT}/scripts/run_m2v2_p2_closed_loop_array.slurm"
SPEC="${ROOT}/protocol/M2V2-P1-P2-FEASIBILITY-SPEC-2026-08-12.md"
STABLEWM_HOME="${ROOT}/data/stablewm"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
: "${SPEC_SHA256:?submit with frozen SPEC_SHA256}"
: "${UNCONDITIONAL_JOB_ID:?submit with M2v2 unconditional job ID}"
: "${REFERENCE_JOB_ID:?submit with completed M2v2 P1-reference job ID}"

SEEDS=(20260728 20260729 20260730)
WEIGHTS=(0.25 0.5 1.0 2.0 4.0)
environment_index=$((SLURM_ARRAY_TASK_ID / 60))
within_environment=$((SLURM_ARRAY_TASK_ID % 60))
weight_index=$((within_environment / 12))
pool_index=$((within_environment % 12))
weight="${WEIGHTS[weight_index]}"
if (( environment_index == 0 )); then
  ENVIRONMENT="pusht"
  CONDITIONAL_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-pusht-v1/true/width-1024"
  CONDITIONAL_JOB_ID=294599
  UNCONDITIONAL_TASK_OFFSET=0
  CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/pusht-v1/p2-stratum3-b0-d75-h2-job-294604"
  DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
  CHECKPOINT="${STABLEWM_HOME}/runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15_object.ckpt"
  EVAL_CONFIG="${CODE}/h_le_wm/config/eval/hi_pusht.yaml"
  POLICY="runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15"
else
  ENVIRONMENT="tworoom"
  CONDITIONAL_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-tworoom-v1/true/width-1024"
  CONDITIONAL_JOB_ID=295652
  UNCONDITIONAL_TASK_OFFSET=3
  CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1/p2-stratum3"
  DATASET="${STABLEWM_HOME}/tworoom.h5"
  CHECKPOINT="${STABLEWM_HOME}/runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15_object.ckpt"
  EVAL_CONFIG="${CODE}/config/eval/hi_tworoom.yaml"
  POLICY="runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15"
fi
UNCONDITIONAL_ROOT="${STABLEWM_HOME}/derived/scorers/m2v2-unconditional-${ENVIRONMENT}-v1/width-1024"
REFERENCE_DIR="${STABLEWM_HOME}/derived/scorer-audits/${ENVIRONMENT}-v1/m2v2-p1-reference-job-${REFERENCE_JOB_ID}"
OUTPUT_ROOT="${STABLEWM_HOME}/derived/closed-loop-development/${ENVIRONMENT}-v1/m2v2-grid-job-${SLURM_ARRAY_JOB_ID}"
OUTPUT_DIR="${OUTPUT_ROOT}/weight-${weight}/pool-$(printf '%02d' "${pool_index}")-task-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-m2v2-p2-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

CONDITIONAL_ARGS=()
UNCONDITIONAL_ARGS=()
CHECKPOINTS=()
for seed_index in 0 1 2; do
  seed="${SEEDS[seed_index]}"
  conditional_task=$((seed_index + 3))
  unconditional_task=$((seed_index + UNCONDITIONAL_TASK_OFFSET))
  conditional="${CONDITIONAL_ROOT}/seed-${seed}-job-${CONDITIONAL_JOB_ID}-${conditional_task}/best-checkpoint.pt"
  unconditional="${UNCONDITIONAL_ROOT}/seed-${seed}-job-${UNCONDITIONAL_JOB_ID}-${unconditional_task}/best-checkpoint.pt"
  CONDITIONAL_ARGS+=(--conditional-checkpoint "${conditional}")
  UNCONDITIONAL_ARGS+=(--unconditional-checkpoint "${unconditional}")
  CHECKPOINTS+=("${conditional}" "${unconditional}")
done
for required in "${IMAGE}" "${SCRIPT}" "${SCORER}" "${CORE_RUNNER}" "${CORE_WRAPPER}" "${RUNNER}" "${SPEC}" \
  "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" \
  "${DATASET}" "${CHECKPOINT}" "${EVAL_CONFIG}" \
  "${REFERENCE_DIR}/reference.npz" "${REFERENCE_DIR}/manifest.json" \
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${CHECKPOINTS[@]}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing M2v2 closed-loop input: ${required}" >&2; exit 2; fi
done
echo "${SPEC_SHA256}  ${SPEC}" | sha256sum -c - >/dev/null
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite M2v2 closed-loop task" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"
{
  echo "classification=${ENVIRONMENT}_p2_m2v2_closed_loop_weight_development"
  echo "partition=P2-development-only"
  echo "array_job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "environment=${ENVIRONMENT}"
  echo "weight=${weight}"
  echo "pool_index=${pool_index}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${SCORER}" "${CORE_RUNNER}" "${CORE_WRAPPER}" "${RUNNER}" "${SPEC}" \
    "${CANDIDATE_DIR}/manifest.json" "${DATASET}" "${CHECKPOINT}" "${EVAL_CONFIG}" \
    "${REFERENCE_DIR}/reference.npz" "${REFERENCE_DIR}/manifest.json" \
    "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${CHECKPOINTS[@]}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts:'"${CODE}"'/scripts/diagnostics:'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=20260728
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export EVAL_DETERMINISM=strict
    export TMPDIR="'"${JOB_TMP}"'"
    export MPLBACKEND=Agg
    export MUJOCO_GL=egl
    export SDL_VIDEODRIVER=dummy
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" --environment "'"${ENVIRONMENT}"'" \
      --candidate-dir "'"${CANDIDATE_DIR}"'" --dataset "'"${DATASET}"'" \
      --checkpoint-file "'"${CHECKPOINT}"'" --policy "'"${POLICY}"'" \
      --stablewm-home "'"${STABLEWM_HOME}"'" --eval-config "'"${EVAL_CONFIG}"'" \
      --weight "'"${weight}"'" --pool-index "'"${pool_index}"'" \
      '"${CONDITIONAL_ARGS[*]}"' '"${UNCONDITIONAL_ARGS[*]}"' \
      --reference-npz "'"${REFERENCE_DIR}"'/reference.npz" \
      --reference-manifest "'"${REFERENCE_DIR}"'/manifest.json" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --spec "'"${SPEC}"'" --output-h5 "'"${OUTPUT_DIR}"'/result.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" --m2v2-batch-size 8192
  '

test -s "${OUTPUT_DIR}/result.h5"
test -s "${OUTPUT_DIR}/manifest.json"
grep -q '"method": "M2v2"' "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
