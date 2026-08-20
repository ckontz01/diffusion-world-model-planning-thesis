#!/usr/bin/env bash

# Score each frozen candidate trajectory from one shared world-model rollout.

#SBATCH --job-name=acid-alt-pusht-d1-score
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-score-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-d1-score-%j.err

set -euo pipefail
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${CAPTURE_JOB_ID:?submit with candidate-capture job ID}"
: "${CORE_SCORER_JOB_ID:?submit with core scorer array job ID}"
: "${REACHABILITY_JOB_ID:?submit with reachability array job ID}"
: "${CONTROL_JOB_ID:?submit with control array job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
CORE_SNAPSHOT="${ROOT}/snapshots/acid-alternative-v1-28ca7d9c0863ceb9"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
CHECKPOINT="${STABLEWM_HOME}/pusht/lewm_hf_22b330c_object.ckpt"
CAPTURE="${ROOT}/results/acid-alternative/diagnostics/pusht/d1-b0-candidate-pools/planner-seed-7101-job-${CAPTURE_JOB_ID}"
OUTPUT="${ROOT}/results/acid-alternative/diagnostics/pusht/d1-candidate-scores/job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-pusht-d1-score-${SLURM_JOB_ID}"
SEEDS=(6101 6102 6103)

for required in \
  "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${SOURCE_MANIFEST}" "${IMAGE}" \
  "${CHECKPOINT}" "${CAPTURE}/candidate-pools.pt" "${CAPTURE}/manifest.json"; do
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

scorer_arguments=()
for index in 0 1 2; do
  seed="${SEEDS[${index}]}"
  scorer_arguments+=(--scorer "acid-true-${seed}=acid=${ROOT}/results/acid-alternative/scorers/pusht/acid/true/seed-${seed}-job-${CORE_SCORER_JOB_ID}-${index}/best.pt")
  scorer_arguments+=(--scorer "reachability-true-${seed}=reachability=${ROOT}/results/acid-alternative/scorers/pusht/reachability/true/seed-${seed}-job-${REACHABILITY_JOB_ID}-${index}/best.pt")
  scorer_arguments+=(--scorer "reachability-shuffled-${seed}=reachability=${ROOT}/results/acid-alternative/scorers/pusht/reachability/shuffled_label/seed-${seed}-job-${REACHABILITY_JOB_ID}-$((3 + index))/best.pt")
  scorer_arguments+=(--scorer "diffusion-true-${seed}=diffusion=${ROOT}/results/acid-alternative/scorers/pusht/diffusion/true/seed-${seed}-job-${CORE_SCORER_JOB_ID}-$((3 + index))/best.pt")
  scorer_arguments+=(--scorer "forward-true-${seed}=forward=${ROOT}/results/acid-alternative/scorers/pusht/forward/true/seed-${seed}-job-${CORE_SCORER_JOB_ID}-$((6 + index))/best.pt")
  scorer_arguments+=(--scorer "diffusion-shuffled-${seed}=diffusion=${ROOT}/results/acid-alternative/scorers/pusht/diffusion/shuffled_action/seed-${seed}-job-${CONTROL_JOB_ID}-${index}/best.pt")
  scorer_arguments+=(--scorer "forward-shuffled-${seed}=forward=${ROOT}/results/acid-alternative/scorers/pusht/forward/shuffled_action/seed-${seed}-job-${CONTROL_JOB_ID}-$((3 + index))/best.pt")
  scorer_arguments+=(--scorer "diffusion-action-ablated-${seed}=diffusion=${ROOT}/results/acid-alternative/scorers/pusht/diffusion/action_ablated/seed-${seed}-job-${CONTROL_JOB_ID}-$((6 + index))/best.pt")
done
for ((index = 1; index < ${#scorer_arguments[@]}; index += 2)); do
  declaration="${scorer_arguments[${index}]}"
  checkpoint_path="${declaration#*=}"
  checkpoint_path="${checkpoint_path#*=}"
  test -f "${checkpoint_path}"
done
nvidia-smi
apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -s -- \
  "${DIAG_SNAPSHOT}" "${CORE_SNAPSHOT}" "${CODE}" "${TOOLS_DIR}" "${ENV_DIR}" \
  "${STABLEWM_HOME}" "${CHECKPOINT}" "${SOURCE_MANIFEST}" "${CAPTURE}" \
  "${OUTPUT}" "${JOB_TMP}" "${SLURM_JOB_ID}" "${scorer_arguments[@]}" <<'CONTAINER'
set -euo pipefail
DIAG_SNAPSHOT="$1"; shift
CORE_SNAPSHOT="$1"; shift
CODE="$1"; shift
TOOLS_DIR="$1"; shift
ENV_DIR="$1"; shift
STABLEWM_HOME="$1"; shift
CHECKPOINT="$1"; shift
SOURCE_MANIFEST="$1"; shift
CAPTURE="$1"; shift
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
python -m acid_alternative_diagnostics.score_candidate_pools \
  --candidate-artifact "${CAPTURE}/candidate-pools.pt" \
  --candidate-manifest "${CAPTURE}/manifest.json" \
  --stablewm-home "${STABLEWM_HOME}" \
  --world-model-policy pusht/lewm_hf_22b330c \
  --world-model-checkpoint "${CHECKPOINT}" \
  --source-manifest "${SOURCE_MANIFEST}" \
  --lambda-weight 0.07 \
  --diffusion-sigma 0.10 \
  --diffusion-sigma 0.25 \
  --diffusion-sigma 0.50 \
  --output-dir "${OUTPUT}" \
  "$@"
CONTAINER
mv "${JOB_TMP}/source-provenance.sha256" "${OUTPUT}/source-provenance.sha256"
sha256sum "${OUTPUT}/candidate-scores.pt" "${OUTPUT}/manifest.json" \
  "${OUTPUT}/source-provenance.sha256" > "${OUTPUT}/sha256.txt"
