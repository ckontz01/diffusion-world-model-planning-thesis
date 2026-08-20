#!/usr/bin/env bash

# Predeclared D1 or locked post-primary C1 budget, lambda, and sigma sensitivity.

#SBATCH --job-name=acid-alt-task-sensitivity
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=24:00:00
#SBATCH --array=0-104%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-sensitivity-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-sensitivity-%A_%a.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${ANALYSIS_ROLE:?submit with ANALYSIS_ROLE=D1|C1}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${ORCH_SNAPSHOT:?submit with immutable orchestration snapshot path}"
: "${CORE_SCORER_JOB_ID:?submit with core scorer array ID}"
: "${REACHABILITY_JOB_ID:?submit with reachability array ID}"
: "${PRIMARY_MATRIX_JOB_ID:?submit with completed primary matrix ID}"
[[ "${ANALYSIS_ROLE}" == D1 || "${ANALYSIS_ROLE}" == C1 ]] || { echo "invalid ANALYSIS_ROLE" >&2; exit 2; }
namespace="${ANALYSIS_ROLE,,}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
ANALYSIS_MANIFEST="${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"
ORCHESTRATION_MANIFEST="${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"
CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"
if [[ "${ANALYSIS_ROLE}" == D1 ]]; then
  manifest_name=d1-fresh-development.tsv
else
  manifest_name=c1-locked-confirmation.tsv
  : "${CONFIRMATION_AUTHORIZATION:?C1 sensitivity requires authorization}"
  : "${PRIMARY_ANALYSIS_JOB_ID:?C1 sensitivity requires locked primary analysis ID}"
  PRIMARY_ANALYSIS="${ROOT}/results/acid-alternative/analysis/c1/closed-loop/job-${PRIMARY_ANALYSIS_JOB_ID}/summary.json"
  test -f "${PRIMARY_ANALYSIS}"
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" "${ENV_DIR}/bin/python" - "${PRIMARY_ANALYSIS}" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if payload.get("status") != "ok" or payload.get("kind") != "matched_five_arm_closed_loop_analysis" or payload.get("role") != "confirmation":
    raise SystemExit("C1 primary analysis is not a complete locked confirmation analysis")
PY
fi
MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/${manifest_name}"
IDENTIFICATION_MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-episodes.tsv"
IDENTIFICATION_SUMMARY="${ROOT}/manifests/acid-alternative-v1/${TASK}/i1-confirmation-identification-summary.json"
arms=(b0 acid reachability diffusion forward)
seeds=(6101 6102 6103)
planner_seeds=(7101 7102 7103)
for index in $(seq 0 14); do
  arm_index=$((index / 3)); seed_index=$((index % 3))
  test -f "${ROOT}/results/acid-alternative/${namespace}/${TASK}/${arms[${arm_index}]}/train-seed-${seeds[${seed_index}]}-planner-seed-${planner_seeds[${seed_index}]}-job-${PRIMARY_MATRIX_JOB_ID}-${index}/summary.json"
done
settings=(); setting_arms=(); setting_seeds=(); populations=(); topks=(); lambdas=(); diffusion_sigmas=()
for spec in "pop30:30:3" "pop50:50:5" "pop150:150:15" "pop300:300:30"; do
  IFS=: read -r label population topk <<< "${spec}"
  for arm in "${arms[@]}"; do for seed_index in 0 1 2; do
    settings+=("${label}-lambda007"); setting_arms+=("${arm}"); setting_seeds+=("${seed_index}")
    populations+=("${population}"); topks+=("${topk}"); lambdas+=(0.07); diffusion_sigmas+=(multi)
  done; done
done
for spec in "lambda0005:0.005" "lambda004:0.04" "lambda010:0.10"; do
  IFS=: read -r label weight <<< "${spec}"
  for arm in acid reachability diffusion forward; do for seed_index in 0 1 2; do
    settings+=("pop300-${label}"); setting_arms+=("${arm}"); setting_seeds+=("${seed_index}")
    populations+=(300); topks+=(30); lambdas+=("${weight}"); diffusion_sigmas+=(multi)
  done; done
done
for spec in "sigma010:0.10" "sigma025:0.25" "sigma050:0.50"; do
  IFS=: read -r label sigma <<< "${spec}"
  for seed_index in 0 1 2; do
    settings+=("pop300-lambda007-${label}"); setting_arms+=(diffusion); setting_seeds+=("${seed_index}")
    populations+=(300); topks+=(30); lambdas+=(0.07); diffusion_sigmas+=("${sigma}")
  done
done
[[ ${#settings[@]} -eq 105 ]] || { echo "internal sensitivity matrix error" >&2; exit 2; }
INDEX="${SLURM_ARRAY_TASK_ID}"
SETTING="${settings[${INDEX}]}"; ARM="${setting_arms[${INDEX}]}"; SEED_INDEX="${setting_seeds[${INDEX}]}"
POPULATION="${populations[${INDEX}]}"; TOPK="${topks[${INDEX}]}"; LAMBDA="${lambdas[${INDEX}]}"; DIFFUSION_SIGMA="${diffusion_sigmas[${INDEX}]}"
SEED="${seeds[${SEED_INDEX}]}"; PLANNER_SEED="${planner_seeds[${SEED_INDEX}]}"; SCORER=""
case "${ARM}" in
  b0) ;;
  acid) SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-${SEED_INDEX}/best.pt" ;;
  reachability) SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/reachability/true/seed-${SEED}-job-${REACHABILITY_JOB_ID}-${SEED_INDEX}/best.pt" ;;
  diffusion) SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/diffusion/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-$((3 + SEED_INDEX))/best.pt" ;;
  forward) SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-${SEED}-job-${CORE_SCORER_JOB_ID}-$((6 + SEED_INDEX))/best.pt" ;;
  *) exit 2 ;;
esac
for required in "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${IMAGE}" "${DATASET}" "${CHECKPOINT}" "${MANIFEST}"; do test -f "${required}"; done
if [[ "${ANALYSIS_ROLE}" == C1 ]]; then test -f "${IDENTIFICATION_MANIFEST}"; test -f "${IDENTIFICATION_SUMMARY}"; fi
if [[ -n "${SCORER}" ]]; then test -f "${SCORER}"; fi
if [[ "${ANALYSIS_ROLE}" == C1 ]]; then
  test -f "${CONFIRMATION_AUTHORIZATION}"
  verify_arguments=(--authorization "${CONFIRMATION_AUTHORIZATION}" --task "${TASK}" --arm "${ARM}" --seed "${SEED}" --source-manifest "${SOURCE_MANIFEST}" --analysis-manifest "${ANALYSIS_MANIFEST}" --orchestration-manifest "${ORCHESTRATION_MANIFEST}" --eval-manifest "${MANIFEST}" --world-model-checkpoint "${CHECKPOINT}" --identification-manifest "${IDENTIFICATION_MANIFEST}" --identification-summary "${IDENTIFICATION_SUMMARY}")
  if [[ -n "${SCORER}" ]]; then verify_arguments+=(--scorer-checkpoint "${SCORER}"); fi
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.verify_c1_authorization "${verify_arguments[@]}"
fi
OUTPUT="${ROOT}/results/acid-alternative/sensitivity/${namespace}/${TASK}/${SETTING}/${ARM}/train-seed-${SEED}-planner-seed-${PLANNER_SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-${namespace}-sensitivity-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"; trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
arguments=(--arm "${ARM}" --code-root "${CODE}" --eval-config-name "${EVAL_CONFIG_NAME}" --stablewm-home "${STABLEWM_HOME}" --dataset "${DATASET}" --dataset-name "${DATASET_NAME}" --world-model-policy "${WORLD_MODEL_POLICY}" --world-model-checkpoint "${CHECKPOINT}" --source-manifest "${SOURCE_MANIFEST}" --eval-manifest "${MANIFEST}" --planner-seed "${PLANNER_SEED}" --lambda-weight "${LAMBDA}" --goal-offset 25 --eval-budget 50 --horizon 5 --receding-horizon 5 --action-block 5 --cem-samples "${POPULATION}" --cem-steps 30 --cem-topk "${TOPK}" --output-dir "${OUTPUT}")
if [[ "${ANALYSIS_ROLE}" == C1 ]]; then arguments+=(--confirmation-authorization "${CONFIRMATION_AUTHORIZATION}"); fi
if [[ -n "${SCORER}" ]]; then arguments+=(--scorer-checkpoint "${SCORER}"); fi
if [[ "${DIFFUSION_SIGMA}" != multi ]]; then arguments+=(--diffusion-sigma "${DIFFUSION_SIGMA}"); fi
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" PYTHONHASHSEED="${PLANNER_SEED}" CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg SLURM_JOB_ID="${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" python -m acid_alternative.evaluate_matched "${arguments[@]}"
printf '%s\n' "task=${TASK}" "analysis_role=${ANALYSIS_ROLE}" "setting=${SETTING}" "arm=${ARM}" "seed=${SEED}" "population=${POPULATION}" "topk=${TOPK}" "lambda=${LAMBDA}" "diffusion_sigma=${DIFFUSION_SIGMA}" "primary_matrix_job=${PRIMARY_MATRIX_JOB_ID}" "primary_analysis_job=${PRIMARY_ANALYSIS_JOB_ID:-not-applicable}" "authorization=${CONFIRMATION_AUTHORIZATION:-not-applicable}" > "${OUTPUT}/provenance.txt"
checksum_inputs=("$0" "${SOURCE_MANIFEST}" "${ANALYSIS_MANIFEST}" "${ORCHESTRATION_MANIFEST}" "${OUTPUT}/summary.json" "${OUTPUT}/episodes.tsv" "${OUTPUT}/resolved-config.json" "${OUTPUT}/cem-diagnostics.jsonl" "${OUTPUT}/provenance.txt")
if [[ "${ANALYSIS_ROLE}" == C1 ]]; then checksum_inputs+=("${CONFIRMATION_AUTHORIZATION}" "${PRIMARY_ANALYSIS}"); fi
sha256sum "${checksum_inputs[@]}" > "${OUTPUT}/sha256.txt"
