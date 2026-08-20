#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p2-b0-cap-smoke
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-b0-cap-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p2-b0-cap-smoke-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/capture_p2_b0_candidate_pools.py"
RUNNER="${ROOT}/scripts/run_tworoom_p2_b0_candidate_capture_smoke.slurm"
LATENT_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-tworoom-epoch15/p2"
PARTITIONS="${ROOT}/manifests/partitions/tworoom-v1/episodes-seed-20260728.tsv"
CHECKPOINT="${STABLEWM_HOME}/runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15_object.ckpt"
OUTPUT_DIR="${STABLEWM_HOME}/derived/candidate-pools/tworoom-v1/p2-stratum3-smoke-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-p2-b0-capture-smoke-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="ebccf6add034322a29fbafeb333e3c5997a7b6a5fa4284940362b5fa7ff8b9fb"
EXPECTED_PARTITIONS_SHA256="47971097b1979798345c298d91eb36f91a0884353789b7f8736e6a1f9e79f790"
EXPECTED_CHECKPOINT_SHA256="5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LATENT_DIR}/latents.h5" \
  "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" "${PARTITIONS}" "${CHECKPOINT}"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom P2 capture-smoke input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_PARTITIONS_SHA256}  ${PARTITIONS}" | sha256sum -c -
echo "${EXPECTED_CHECKPOINT_SHA256}  ${CHECKPOINT}" | sha256sum -c -
(cd "${LATENT_DIR}" && sha256sum -c checksums.sha256 >/dev/null)
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite capture smoke" >&2; exit 2; fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p2_stratum3_capture_implementation_smoke"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${LATENT_DIR}/latents.h5" \
    "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" "${PARTITIONS}" "${CHECKPOINT}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm:'"${CODE}"'/scripts/diagnostics"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=42
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export EVAL_DETERMINISM=strict
    export TMPDIR="'"${JOB_TMP}"'"
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" \
      --environment tworoom --code-root "'"${CODE}"'" --stablewm-home "'"${STABLEWM_HOME}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --partition-manifest "'"${PARTITIONS}"'" --partition P2 \
      --policy runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15 \
      --checkpoint-file "'"${CHECKPOINT}"'" --seed 20260728 \
      --pool-count 1 --candidate-count 8 --goal-offset 25 \
      --high-horizon 2 --high-action-block 1 --high-num-samples 64 --high-iters 2 --high-topk 8 \
      --smoke --repeat-check \
      --output-h5 "'"${OUTPUT_DIR}"'/candidate-pools.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json"
  '

test -s "${OUTPUT_DIR}/candidate-pools.h5"
test -s "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
