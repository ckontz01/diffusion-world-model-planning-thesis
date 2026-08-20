#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p2-exec-smoke
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-exec-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-exec-smoke-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
REAL_SCRIPT="${ROOT}/scripts/execute_p2_real_frame_candidates.py"
IMAGINED_SCRIPT="${ROOT}/scripts/execute_fixed_subgoal_candidates.py"
RUNNER="${ROOT}/scripts/run_tworoom_p2_candidate_execution_smoke.slurm"
REAL_CANDIDATES="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1/p2-real-frame"
IMAGINED_CANDIDATES="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1/p2-stratum3"
STATS_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-tworoom-epoch15/p1-train-stats"
DATASET="${STABLEWM_HOME}/tworoom.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15_object.ckpt"
OUTPUT_ROOT="${STABLEWM_HOME}/repro/tworoom-p2-candidate-execution-smoke-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-p2-exec-smoke-${SLURM_JOB_ID}"

EXPECTED_REAL_SCRIPT_SHA256="41d47f266b3a4f86b5a632b7a0a49179a68be2fcd1526f0c65306bb44bea1a95"
EXPECTED_IMAGINED_SCRIPT_SHA256="f1ddb5d09104f0cd94f0beda28b7ab342efd1bccc51e2839b7107812434e0023"
EXPECTED_CHECKPOINT_SHA256="5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"

for required in "${IMAGE}" "${REAL_SCRIPT}" "${IMAGINED_SCRIPT}" "${RUNNER}" \
  "${REAL_CANDIDATES}/candidate-pools.h5" "${REAL_CANDIDATES}/manifest.json" "${REAL_CANDIDATES}/checksums.sha256" \
  "${IMAGINED_CANDIDATES}/candidate-pools.h5" "${IMAGINED_CANDIDATES}/manifest.json" "${IMAGINED_CANDIDATES}/checksums.sha256" \
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
  "${DATASET}" "${CHECKPOINT}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom P2 execution-smoke input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_REAL_SCRIPT_SHA256}  ${REAL_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_IMAGINED_SCRIPT_SHA256}  ${IMAGINED_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_CHECKPOINT_SHA256}  ${CHECKPOINT}" | sha256sum -c -
(cd "${REAL_CANDIDATES}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${IMAGINED_CANDIDATES}" && sha256sum -c checksums.sha256 >/dev/null)
(cd "${STATS_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_ROOT}" ]]; then echo "Refusing to overwrite TwoRoom execution smoke" >&2; exit 2; fi

mkdir -p "${OUTPUT_ROOT}/real" "${OUTPUT_ROOT}/imagined" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p2_candidate_execution_implementation_smoke"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${REAL_SCRIPT}" "${IMAGINED_SCRIPT}" "${RUNNER}" \
    "${REAL_CANDIDATES}/candidate-pools.h5" "${REAL_CANDIDATES}/manifest.json" \
    "${IMAGINED_CANDIDATES}/candidate-pools.h5" "${IMAGINED_CANDIDATES}/manifest.json" \
    "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${DATASET}" "${CHECKPOINT}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_ROOT}/provenance.txt"

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
    python "'"${REAL_SCRIPT}"'" --environment tworoom --partition P2 \
      --candidate-h5 "'"${REAL_CANDIDATES}"'/candidate-pools.h5" --candidate-manifest "'"${REAL_CANDIDATES}"'/manifest.json" \
      --dataset "'"${DATASET}"'" --stablewm-home "'"${STABLEWM_HOME}"'" \
      --eval-config "'"${CODE}"'/config/eval/hi_tworoom.yaml" \
      --policy runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15 \
      --checkpoint-file "'"${CHECKPOINT}"'" --stats-npz "'"${STATS_DIR}"'/stats.npz" --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --stratum-index 0 --pool-index 0 --repeat-index 0 --candidate-start 0 --candidate-count 2 \
      --low-num-samples 64 --low-iters 2 --low-topk 8 --cost-env-chunk-size 16 --smoke \
      --output-h5 "'"${OUTPUT_ROOT}"'/real/executions.h5" --output-json "'"${OUTPUT_ROOT}"'/real/manifest.json"
    python "'"${IMAGINED_SCRIPT}"'" --environment tworoom --partition P2 \
      --candidate-h5 "'"${IMAGINED_CANDIDATES}"'/candidate-pools.h5" --candidate-manifest "'"${IMAGINED_CANDIDATES}"'/manifest.json" \
      --dataset "'"${DATASET}"'" --stablewm-home "'"${STABLEWM_HOME}"'" \
      --eval-config "'"${CODE}"'/config/eval/hi_tworoom.yaml" \
      --policy runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15 \
      --checkpoint-file "'"${CHECKPOINT}"'" --stats-npz "'"${STATS_DIR}"'/stats.npz" --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --pool-index 0 --repeat-index 0 --candidate-start 0 --candidate-count 2 \
      --low-num-samples 64 --low-iters 2 --low-topk 8 --cost-env-chunk-size 16 --smoke \
      --output-h5 "'"${OUTPUT_ROOT}"'/imagined/executions.h5" --output-json "'"${OUTPUT_ROOT}"'/imagined/manifest.json"
  '

test -s "${OUTPUT_ROOT}/real/executions.h5"
test -s "${OUTPUT_ROOT}/real/manifest.json"
test -s "${OUTPUT_ROOT}/imagined/executions.h5"
test -s "${OUTPUT_ROOT}/imagined/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_ROOT}/provenance.txt"
find "${OUTPUT_ROOT}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_ROOT}/checksums.sha256"
sha256sum -c "${OUTPUT_ROOT}/checksums.sha256"
