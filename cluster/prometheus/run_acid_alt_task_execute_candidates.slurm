#!/usr/bin/env bash

# Execute every frozen diagnostic candidate in the task's real simulator.

#SBATCH --job-name=acid-alt-task-execute
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=16:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-execute-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-execute-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${ANALYSIS_ROLE:?submit with ANALYSIS_ROLE=D1|C1}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${ORCH_SNAPSHOT:?submit with immutable orchestration snapshot path}"
: "${CAPTURE_JOB_ID:?submit with candidate-capture job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
[[ "${ANALYSIS_ROLE}" == D1 || "${ANALYSIS_ROLE}" == C1 ]] || { echo "invalid ANALYSIS_ROLE" >&2; exit 2; }
namespace="${ANALYSIS_ROLE,,}"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
ORCHESTRATION_MANIFEST="${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"
CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"
if [[ "${ANALYSIS_ROLE}" == D1 ]]; then manifest_name=d1-fresh-development.tsv; else manifest_name=c1-locked-confirmation.tsv; : "${CONFIRMATION_AUTHORIZATION:?C1 execution requires authorization}"; fi
MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/${manifest_name}"
IDENTIFICATION_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-episodes.tsv"
IDENTIFICATION_SUMMARY="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-summary.json"
CAPTURE="${ROOT}/results/acid-alternative/diagnostics/${TASK}/${namespace}-b0-candidate-pools/planner-seed-7101-job-${CAPTURE_JOB_ID}"
OUTPUT="${ROOT}/results/acid-alternative/diagnostics/${TASK}/${namespace}-candidate-executions/job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-execute-${SLURM_JOB_ID}"
for required in "${SOURCE_MANIFEST}" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${IMAGE}" "${DATASET}" "${CHECKPOINT}" "${MANIFEST}" "${CAPTURE}/candidate-pools.pt" "${CAPTURE}/manifest.json"; do test -f "${required}"; done
if [[ "${ANALYSIS_ROLE}" == C1 ]]; then
  test -f "${CONFIRMATION_AUTHORIZATION}"
  test -f "${ORCHESTRATION_MANIFEST}"
  test -f "${IDENTIFICATION_MANIFEST}"
  test -f "${IDENTIFICATION_SUMMARY}"
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.verify_c1_authorization --authorization "${CONFIRMATION_AUTHORIZATION}" --task "${TASK}" --arm b0 --seed 6101 --source-manifest "${SOURCE_MANIFEST}" --analysis-manifest "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" --orchestration-manifest "${ORCHESTRATION_MANIFEST}" --eval-manifest "${MANIFEST}" --world-model-checkpoint "${CHECKPOINT}" --identification-manifest "${IDENTIFICATION_MANIFEST}" --identification-summary "${IDENTIFICATION_SUMMARY}"
fi
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  python -m acid_alternative_diagnostics.execute_candidate_pools \
  --candidate-artifact "${CAPTURE}/candidate-pools.pt" --candidate-manifest "${CAPTURE}/manifest.json" \
  --code-root "${CODE}" --eval-config-name "${EVAL_CONFIG_NAME}" --stablewm-home "${STABLEWM_HOME}" \
  --dataset "${DATASET}" --dataset-name "${DATASET_NAME}" --world-model-policy "${WORLD_MODEL_POLICY}" \
  --world-model-checkpoint "${CHECKPOINT}" --source-manifest "${SOURCE_MANIFEST}" --goal-offset 25 --output-dir "${OUTPUT}"
printf '%s\n' "task=${TASK}" "analysis_role=${ANALYSIS_ROLE}" "capture_job_id=${CAPTURE_JOB_ID}" "authorization=${CONFIRMATION_AUTHORIZATION:-not-applicable}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"
checksum_inputs=("$0" "${SOURCE_MANIFEST}" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${ORCHESTRATION_MANIFEST}" "${OUTPUT}/candidate-executions.h5" "${OUTPUT}/manifest.json" "${OUTPUT}/provenance.txt")
if [[ "${ANALYSIS_ROLE}" == C1 ]]; then checksum_inputs+=("${CONFIRMATION_AUTHORIZATION}"); fi
sha256sum "${checksum_inputs[@]}" > "${OUTPUT}/sha256.txt"
