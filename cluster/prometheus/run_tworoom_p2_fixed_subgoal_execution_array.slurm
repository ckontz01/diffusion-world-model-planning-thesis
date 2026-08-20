#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p2-subgoal-exec
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --array=0-59%4
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-subgoal-exec-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-subgoal-exec-%A_%a.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/execute_fixed_subgoal_candidates.py"
RUNNER="${ROOT}/scripts/run_tworoom_p2_fixed_subgoal_execution_array.slurm"
CANDIDATE_DIR="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1/p2-stratum3"
STATS_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-tworoom-epoch15/p1-train-stats"
DATASET="${STABLEWM_HOME}/tworoom.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15_object.ckpt"

POOL_INDEX=$((SLURM_ARRAY_TASK_ID / 5))
REPEAT_INDEX=$((SLURM_ARRAY_TASK_ID % 5))
printf -v POOL_PAD "%02d" "${POOL_INDEX}"
OUTPUT_ROOT="${STABLEWM_HOME}/derived/candidate-executions/tworoom-v1/p2-stratum3-job-${SLURM_ARRAY_JOB_ID}"
OUTPUT_DIR="${OUTPUT_ROOT}/pool-${POOL_PAD}-repeat-${REPEAT_INDEX}"
JOB_TMP="/tmp/ckontzias-tworoom-p2-subgoal-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

EXPECTED_SCRIPT_SHA256="f1ddb5d09104f0cd94f0beda28b7ab342efd1bccc51e2839b7107812434e0023"
EXPECTED_CHECKPOINT_SHA256="5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${CANDIDATE_DIR}/candidate-pools.h5" \
  "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256" \
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
  "${DATASET}" "${CHECKPOINT}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom P2 subgoal-execution input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_CHECKPOINT_SHA256}  ${CHECKPOINT}" | sha256sum -c -
(cd "${CANDIDATE_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${STATS_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite TwoRoom subgoal execution task" >&2; exit 2; fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p2_fixed_subgoal_candidate_attainment_execution"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "pool_index=${POOL_INDEX}"
  echo "repeat_index=${REPEAT_INDEX}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${CANDIDATE_DIR}/candidate-pools.h5" \
    "${CANDIDATE_DIR}/manifest.json" "${CANDIDATE_DIR}/checksums.sha256" \
    "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
    "${DATASET}" "${CHECKPOINT}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts:'"${CODE}"':'"${CODE}"'/third_party/lewm:'"${CODE}"'/scripts/diagnostics"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=42
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export EVAL_DETERMINISM=strict
    export TMPDIR="'"${JOB_TMP}"'"
    export MPLBACKEND=Agg
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" --environment tworoom --partition P2 \
      --candidate-h5 "'"${CANDIDATE_DIR}"'/candidate-pools.h5" --candidate-manifest "'"${CANDIDATE_DIR}"'/manifest.json" \
      --dataset "'"${DATASET}"'" --stablewm-home "'"${STABLEWM_HOME}"'" --eval-config "'"${CODE}"'/config/eval/hi_tworoom.yaml" \
      --policy runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15 --checkpoint-file "'"${CHECKPOINT}"'" \
      --stats-npz "'"${STATS_DIR}"'/stats.npz" --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --pool-index "'"${POOL_INDEX}"'" --repeat-index "'"${REPEAT_INDEX}"'" \
      --candidate-start 0 --candidate-count 64 --low-num-samples 300 --low-iters 30 --low-topk 10 --cost-env-chunk-size 16 \
      --output-h5 "'"${OUTPUT_DIR}"'/executions.h5" --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/executions.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
