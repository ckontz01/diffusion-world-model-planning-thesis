#!/usr/bin/env bash

# 3 scorer arms x 5 weights x 12 shared TwoRoom P2 D25 queries.

#SBATCH --job-name=tworoom-p2-aug-grid
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --array=0-179%3
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-aug-grid-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-aug-grid-%A_%a.err

set -euo pipefail
: "${TRUE_SCORE_JOB_ID:?submit with TRUE_SCORE_JOB_ID set to the completed TwoRoom P2 true-scorer selection job}"
: "${CALIBRATION_JOB_ID:?submit with CALIBRATION_JOB_ID set to the completed TwoRoom P2 calibration job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
SCRIPT="${ROOT}/scripts/run_p2_augmented_closed_loop_query.py"
WRAPPER="${ROOT}/scripts/feasibility_augmented_high_cost.py"
EXECUTION_HELPER="${ROOT}/scripts/execute_fixed_subgoal_candidates.py"
SELECTION_HELPER="${ROOT}/scripts/score_and_select_p2_true_scorers.py"
M1_HELPER="${ROOT}/scripts/train_m1_macro_cycle_head.py"
M2_HELPER="${ROOT}/scripts/train_m2_diffusion_head.py"
M3_HELPER="${ROOT}/scripts/train_m3_temporal_head.py"
RUNNER="${ROOT}/scripts/run_tworoom_p2_augmented_closed_loop_array.slurm"
AMENDMENTS="${ROOT}/protocol/PROTOCOL-IMPLEMENTATION-AMENDMENTS-2026-08-08.md"
STABLEWM_HOME="${ROOT}/data/stablewm"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1/p2-stratum3"
TRUE_DIR="${STABLEWM_HOME}/derived/scorer-audits/tworoom-v1/p2-true-selection-job-${TRUE_SCORE_JOB_ID}"
CALIBRATION_DIR="${STABLEWM_HOME}/derived/scorer-audits/tworoom-v1/p2-null-control-calibration-job-${CALIBRATION_JOB_ID}"
M1_ROOT="${STABLEWM_HOME}/runs/scorers/m1/tworoom-v1"
M2_ROOT="${STABLEWM_HOME}/derived/scorers/m2-diffusion-tworoom-v1"
M3_ROOT="${STABLEWM_HOME}/derived/scorers/m3-trm-tworoom-v1"
NOISE_DIR="${ROOT}/manifests/scorers/pusht-v1/m2-score-noise-seed-20260728"
DATASET="${STABLEWM_HOME}/tworoom.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15_object.ckpt"
EVAL_CONFIG="${CODE}/config/eval/hi_tworoom.yaml"
OUTPUT_ROOT="${STABLEWM_HOME}/derived/closed-loop-development/tworoom-v1/augmented-grid-job-${SLURM_ARRAY_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-p2-aug-grid-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

EXPECTED_SCRIPT_SHA256="cff14fef29775e1679975ee8103d0859d1259bb03880aa7c66b385e7447560cd"
EXPECTED_WRAPPER_SHA256="5645a2cdd6dca588a5fed6be87942195c1d69d597b38e48867a79f648b476d7c"
EXPECTED_EXECUTION_HELPER_SHA256="f1ddb5d09104f0cd94f0beda28b7ab342efd1bccc51e2839b7107812434e0023"
EXPECTED_SELECTION_HELPER_SHA256="57be0645a9e7a671a40a18d23994e3ff04a7af0f8c0a445eba726d3925ba141d"
EXPECTED_M1_HELPER_SHA256="e7baf8d66bd77d53a49164592ecdc16e9b1f50b1f86baa473467ba2de9327733"
EXPECTED_M2_HELPER_SHA256="f74f12c945d7542f9af0e8ea0f96247b3beb6338869ab0d0589f7b10a2f69efd"
EXPECTED_M3_HELPER_SHA256="8ab0124a858e8c4f3bb1f47c5020eda0adff2cbd93221ad87c22d1d85144e854"
EXPECTED_CANDIDATE_SHA256="022a16c75bbcaf75a8ea77a98ea226ab7566a714d9b211ad5f9381f261285531"
EXPECTED_DATASET_SHA256="129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623"
EXPECTED_CHECKPOINT_SHA256="5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"
EXPECTED_EVAL_CONFIG_SHA256="13d671d15f31093c623d1e6d4d4448ce2f51bb7c81504dfc225aa48e17ec8da1"

METHODS=(M1 M2 M3)
WEIGHTS=(0.25 0.5 1.0 2.0 4.0)
method_index=$(( SLURM_ARRAY_TASK_ID / 60 ))
within_method=$(( SLURM_ARRAY_TASK_ID % 60 ))
weight_index=$(( within_method / 12 ))
pool_index=$(( within_method % 12 ))
method="${METHODS[method_index]}"
weight="${WEIGHTS[weight_index]}"
OUTPUT_DIR="${OUTPUT_ROOT}/method-${method}/weight-${weight}/pool-$(printf '%02d' "${pool_index}")-task-${SLURM_ARRAY_TASK_ID}"

REQUIRED=(
  "${IMAGE}" "${SCRIPT}" "${WRAPPER}" "${EXECUTION_HELPER}" "${SELECTION_HELPER}"
  "${M1_HELPER}" "${M2_HELPER}" "${M3_HELPER}" "${RUNNER}" "${AMENDMENTS}"
  "${CANDIDATE_DIR}/candidate-pools.h5" "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256"
  "${TRUE_DIR}/scores.h5" "${TRUE_DIR}/manifest.json" "${TRUE_DIR}/checksums.sha256"
  "${CALIBRATION_DIR}/audit-and-calibrators.h5" "${CALIBRATION_DIR}/manifest.json" "${CALIBRATION_DIR}/checksums.sha256"
  "${NOISE_DIR}/noise.npy" "${NOISE_DIR}/manifest.json" "${NOISE_DIR}/checksums.sha256"
  "${DATASET}" "${CHECKPOINT}" "${EVAL_CONFIG}"
)
for required in "${REQUIRED[@]}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing or empty TwoRoom augmented-grid input: ${required}" >&2
    exit 2
  fi
done
for required_dir in "${M1_ROOT}" "${M2_ROOT}" "${M3_ROOT}"; do
  if [[ ! -d "${required_dir}" ]]; then
    echo "Missing TwoRoom scorer root: ${required_dir}" >&2
    exit 2
  fi
done
printf '%s  %s\n' "${EXPECTED_SCRIPT_SHA256}" "${SCRIPT}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_WRAPPER_SHA256}" "${WRAPPER}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_EXECUTION_HELPER_SHA256}" "${EXECUTION_HELPER}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_SELECTION_HELPER_SHA256}" "${SELECTION_HELPER}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_M1_HELPER_SHA256}" "${M1_HELPER}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_M2_HELPER_SHA256}" "${M2_HELPER}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_M3_HELPER_SHA256}" "${M3_HELPER}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_CANDIDATE_SHA256}" "${CANDIDATE_DIR}/candidate-pools.h5" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_DATASET_SHA256}" "${DATASET}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_CHECKPOINT_SHA256}" "${CHECKPOINT}" | sha256sum -c -
printf '%s  %s\n' "${EXPECTED_EVAL_CONFIG_SHA256}" "${EVAL_CONFIG}" | sha256sum -c -
(cd "${CANDIDATE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${TRUE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${CALIBRATION_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${NOISE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite TwoRoom augmented-grid task: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p2_augmented_closed_loop_weight_development"
  echo "array_job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "method=${method}"
  echo "weight=${weight}"
  echo "pool_index=${pool_index}"
  echo "true_score_job_id=${TRUE_SCORE_JOB_ID}"
  echo "calibration_job_id=${CALIBRATION_JOB_ID}"
  sha256sum "${IMAGE}" "${SCRIPT}" "${WRAPPER}" "${EXECUTION_HELPER}" \
    "${SELECTION_HELPER}" "${M1_HELPER}" "${M2_HELPER}" "${M3_HELPER}" \
    "${RUNNER}" "${AMENDMENTS}" "${EVAL_CONFIG}" "${CHECKPOINT}" \
    "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256" \
    "${TRUE_DIR}/manifest.json" "${TRUE_DIR}/checksums.sha256" \
    "${CALIBRATION_DIR}/manifest.json" "${CALIBRATION_DIR}/checksums.sha256" \
    "${NOISE_DIR}/manifest.json" "${NOISE_DIR}/checksums.sha256"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
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
    python "'"${SCRIPT}"'" \
      --environment tworoom --partition P2 \
      --candidate-dir "'"${CANDIDATE_DIR}"'" \
      --true-selection-dir "'"${TRUE_DIR}"'" \
      --calibration-dir "'"${CALIBRATION_DIR}"'" \
      --m1-root "'"${M1_ROOT}"'" \
      --m2-root "'"${M2_ROOT}"'" \
      --m3-root "'"${M3_ROOT}"'" \
      --noise-npy "'"${NOISE_DIR}"'/noise.npy" \
      --noise-manifest "'"${NOISE_DIR}"'/manifest.json" \
      --dataset "'"${DATASET}"'" \
      --checkpoint-file "'"${CHECKPOINT}"'" \
      --policy runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15 \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --eval-config "'"${EVAL_CONFIG}"'" \
      --method "'"${method}"'" --weight "'"${weight}"'" --pool-index "'"${pool_index}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/result.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --m2-batch-size 2048
  '

test -s "${OUTPUT_DIR}/result.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
