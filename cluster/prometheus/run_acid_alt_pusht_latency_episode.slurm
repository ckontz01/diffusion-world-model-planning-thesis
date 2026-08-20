#!/usr/bin/env bash

# Wall-clock single-environment episode timing for all five headline arms.

#SBATCH --job-name=acid-alt-pusht-lat-episode
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-lat-episode-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-lat-episode-%j.err

set -euo pipefail
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${CORE_SCORER_JOB_ID:?submit with core scorer array job ID}"
: "${REACHABILITY_JOB_ID:?submit with reachability array job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
CORE_SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
CHECKPOINT="${STABLEWM_HOME}/pusht/lewm_hf_22b330c_object.ckpt"
MANIFEST="${ROOT}/manifests/acid-alternative-v1/pusht/d1-fresh-development.tsv"
OUTPUT="${ROOT}/results/acid-alternative/latency/pusht/end-to-end-episode/job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-lat-episode-${SLURM_JOB_ID}"
ACID="${ROOT}/results/acid-alternative/scorers/pusht/acid/true/seed-6101-job-${CORE_SCORER_JOB_ID}-0/best.pt"
REACHABILITY="${ROOT}/results/acid-alternative/scorers/pusht/reachability/true/seed-6101-job-${REACHABILITY_JOB_ID}-0/best.pt"
DIFFUSION="${ROOT}/results/acid-alternative/scorers/pusht/diffusion/true/seed-6101-job-${CORE_SCORER_JOB_ID}-3/best.pt"
FORWARD="${ROOT}/results/acid-alternative/scorers/pusht/forward/true/seed-6101-job-${CORE_SCORER_JOB_ID}-6/best.pt"

for required in \
  "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${SOURCE_MANIFEST}" "${IMAGE}" \
  "${DATASET}" "${CHECKPOINT}" "${MANIFEST}" "${ACID}" "${REACHABILITY}" \
  "${DIFFUSION}" "${FORWARD}"; do
  test -f "${required}"
done
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
sha256sum "$0" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${SOURCE_MANIFEST}" \
  > "${JOB_TMP}/source-provenance.sha256"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
nvidia-smi

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -s -- \
  "${DIAG_SNAPSHOT}" "${CORE_SNAPSHOT}" "${CODE}" "${TOOLS_DIR}" "${ENV_DIR}" \
  "${STABLEWM_HOME}" "${DATASET}" "${CHECKPOINT}" "${SOURCE_MANIFEST}" \
  "${MANIFEST}" "${ACID}" "${REACHABILITY}" "${DIFFUSION}" "${FORWARD}" \
  "${OUTPUT}" "${JOB_TMP}" "${SLURM_JOB_ID}" <<'CONTAINER'
set -euo pipefail
DIAG_SNAPSHOT="$1"; shift
CORE_SNAPSHOT="$1"; shift
CODE="$1"; shift
TOOLS_DIR="$1"; shift
ENV_DIR="$1"; shift
STABLEWM_HOME="$1"; shift
DATASET="$1"; shift
CHECKPOINT="$1"; shift
SOURCE_MANIFEST="$1"; shift
MANIFEST="$1"; shift
ACID="$1"; shift
REACHABILITY="$1"; shift
DIFFUSION="$1"; shift
FORWARD="$1"; shift
OUTPUT="$1"; shift
JOB_TMP="$1"; shift
RUN_JOB_ID="$1"; shift
export PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm"
export PYTHONHASHSEED=0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export SLURM_JOB_ID="${RUN_JOB_ID}"
export TMPDIR="${JOB_TMP}"
python -m acid_alternative_diagnostics.benchmark_episode_latency \
  --code-root "${CODE}" \
  --eval-config-name pusht \
  --stablewm-home "${STABLEWM_HOME}" \
  --dataset "${DATASET}" \
  --dataset-name pusht_expert_train \
  --world-model-policy pusht/lewm_hf_22b330c \
  --world-model-checkpoint "${CHECKPOINT}" \
  --source-manifest "${SOURCE_MANIFEST}" \
  --eval-manifest "${MANIFEST}" \
  --planner-seed 7101 \
  --lambda-weight 0.07 \
  --goal-offset 25 \
  --eval-budget 50 \
  --horizon 5 \
  --receding-horizon 5 \
  --action-block 5 \
  --cem-samples 300 \
  --cem-steps 30 \
  --cem-topk 30 \
  --diffusion-sigma 0.10 \
  --diffusion-sigma 0.25 \
  --diffusion-sigma 0.50 \
  --scorer "acid=acid=${ACID}" \
  --scorer "reachability=reachability=${REACHABILITY}" \
  --scorer "diffusion=diffusion=${DIFFUSION}" \
  --scorer "forward=forward=${FORWARD}" \
  --warmup-episodes 1 \
  --measured-episodes 5 \
  --output-dir "${OUTPUT}"
CONTAINER

mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
sha256sum "${OUTPUT}/summary.json" "${OUTPUT}/source-provenance.sha256" \
  > "${OUTPUT}/sha256.txt"
