#!/usr/bin/env bash

# Create the immutable C1 authorization after all D1 evidence is complete.
# This script never submits confirmation work.

set -euo pipefail
if [[ $# -ne 4 ]]; then
  echo "usage: $0 CORE_SNAPSHOT DIAG_SNAPSHOT ORCH_SNAPSHOT D1_SUBMISSION_STATE" >&2
  exit 2
fi
: "${AUTHORIZED_BY:?set the accountable authorizer name}"
: "${DECISION_NOTE:?state why the frozen primary configuration is ready for C1}"
[[ "${ATTEST_C1_OUTCOMES_UNSEEN:-}" == YES ]] || {
  echo "set ATTEST_C1_OUTCOMES_UNSEEN=YES only after confirming no C1 outcome has been run or inspected" >&2
  exit 2
}
CORE_SNAPSHOT="$1"; DIAG_SNAPSHOT="$2"; ORCH_SNAPSHOT="$3"; STATE="$4"
ROOT="${THESIS_ROOT:-/lustreFS/data/superworld/ckontzias/thesis}"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
STABLEWM_HOME="${ROOT}/data/stablewm"
for required in "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${STATE}" "${STATE}.sha256" "${IMAGE}"; do test -f "${required}"; done
for snapshot in "${CORE_SNAPSHOT}" "${DIAG_SNAPSHOT}" "${ORCH_SNAPSHOT}"; do
  (cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done
sha256sum -c "${STATE}.sha256"
for location in "${ROOT}/results/acid-alternative/c1" "${ROOT}/results/acid-alternative/analysis/c1" "${ROOT}/results/acid-alternative/sensitivity/c1" "${ROOT}/results/acid-alternative/identification/c1"; do
  if [[ -d "${location}" ]] && find "${location}" -type f -print -quit | grep -q .; then
    echo "refusing authorization because C1 files already exist under ${location}" >&2
    exit 2
  fi
done
if [[ -d "${STABLEWM_HOME}/derived/acid-alternative-v1" ]] && find "${STABLEWM_HOME}/derived/acid-alternative-v1" -type f \( -path '*/i1-flat-latents-job-*/*' -o -path '*/i1-transition-cache-job-*/*' \) -print -quit | grep -q .; then
  echo "refusing authorization because derived I1 artifacts already exist" >&2
  exit 2
fi
if [[ -d "${ROOT}/results/acid-alternative/diagnostics" ]] && find "${ROOT}/results/acid-alternative/diagnostics" -type f -path '*/c1-*/*' -print -quit | grep -q .; then
  echo "refusing authorization because C1 diagnostic files already exist" >&2
  exit 2
fi

lookup_job() {
  local task="$1" stage="$2" values
  values="$(awk -F '\t' -v task="${task}" -v stage="${stage}" 'NR > 1 && $1 == task && $2 == stage { print $3 }' "${STATE}")"
  [[ "${values}" =~ ^[0-9]+$ ]] || { echo "missing or ambiguous ${task}/${stage} job in ${STATE}: ${values}" >&2; exit 2; }
  printf '%s' "${values}"
}

closed_loop_job="$(lookup_job all closed_loop_development)"
validation_job="$(lookup_job all validation_development)"
mechanism_job="$(lookup_job all mechanism)"
sensitivity_job="$(lookup_job all sensitivity_analysis)"
evidence=(
  --development-evidence "closed_loop=${ROOT}/results/acid-alternative/analysis/d1/closed-loop/job-${closed_loop_job}/summary.json"
  --development-evidence "validation=${ROOT}/results/acid-alternative/analysis/d1/validation-identification/job-${validation_job}/summary.json"
  --development-evidence "mechanism=${ROOT}/results/acid-alternative/analysis/d1/mechanism/job-${mechanism_job}/summary.json"
  --development-evidence "sensitivity=${ROOT}/results/acid-alternative/analysis/d1/sensitivity/job-${sensitivity_job}/summary.json"
)
for ((index=1; index<${#evidence[@]}; index+=2)); do test -f "${evidence[${index}]#*=}"; done

task_inputs=(); scorers=()
for task in pusht reacher cube; do
  core_job="$(lookup_job "${task}" core)"
  reachability_job="$(lookup_job "${task}" reachability)"
  control_job="$(lookup_job "${task}" controls)"
  eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${task}" --format shell)"
  eval_manifest="${ROOT}/manifests/acid-alternative-v1/${task}/c1-locked-confirmation.tsv"
  identification_manifest="${ROOT}/manifests/acid-alternative-v1/${task}/i1-confirmation-identification-episodes.tsv"
  identification_summary="${ROOT}/manifests/acid-alternative-v1/${task}/i1-confirmation-identification-summary.json"
  world_checkpoint="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"
  test -f "${eval_manifest}"; test -f "${identification_manifest}"; test -f "${identification_summary}"; test -f "${world_checkpoint}"
  task_inputs+=(--task-input "${task}=${eval_manifest}=${world_checkpoint}=${identification_manifest}=${identification_summary}")
  seeds=(6101 6102 6103)
  for index in 0 1 2; do
    seed="${seeds[${index}]}"
    scorers+=(--scorer "${task}=acid=${seed}=${ROOT}/results/acid-alternative/scorers/${task}/acid/true/seed-${seed}-job-${core_job}-${index}/best.pt")
    scorers+=(--scorer "${task}=reachability=${seed}=${ROOT}/results/acid-alternative/scorers/${task}/reachability/true/seed-${seed}-job-${reachability_job}-${index}/best.pt")
    scorers+=(--scorer "${task}=reachability_shuffled=${seed}=${ROOT}/results/acid-alternative/scorers/${task}/reachability/shuffled_label/seed-${seed}-job-${reachability_job}-$((3 + index))/best.pt")
    scorers+=(--scorer "${task}=diffusion=${seed}=${ROOT}/results/acid-alternative/scorers/${task}/diffusion/true/seed-${seed}-job-${core_job}-$((3 + index))/best.pt")
    scorers+=(--scorer "${task}=diffusion_shuffled=${seed}=${ROOT}/results/acid-alternative/scorers/${task}/diffusion/shuffled_action/seed-${seed}-job-${control_job}-${index}/best.pt")
    scorers+=(--scorer "${task}=diffusion_action_ablated=${seed}=${ROOT}/results/acid-alternative/scorers/${task}/diffusion/action_ablated/seed-${seed}-job-${control_job}-$((6 + index))/best.pt")
    scorers+=(--scorer "${task}=forward=${seed}=${ROOT}/results/acid-alternative/scorers/${task}/forward/true/seed-${seed}-job-${core_job}-$((6 + index))/best.pt")
    scorers+=(--scorer "${task}=forward_shuffled=${seed}=${ROOT}/results/acid-alternative/scorers/${task}/forward/shuffled_action/seed-${seed}-job-${control_job}-$((3 + index))/best.pt")
  done
done
for ((index=1; index<${#scorers[@]}; index+=2)); do declaration="${scorers[${index}]}"; test -f "${declaration##*=}"; done

AUTH_DIR="${ROOT}/authorizations/acid-alternative-v1"
mkdir -p "${AUTH_DIR}"
AUTHORIZATION="${AUTHORIZATION_OUTPUT:-${AUTH_DIR}/c1-$(date -u +%Y%m%dT%H%M%SZ).json}"
[[ ! -e "${AUTHORIZATION}" ]] || { echo "refusing existing authorization: ${AUTHORIZATION}" >&2; exit 2; }
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.create_c1_authorization \
  --source-manifest "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --analysis-manifest "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --orchestration-manifest "${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --development-submission-state "${STATE}" \
  --authorized-by "${AUTHORIZED_BY}" --decision-note "${DECISION_NOTE}" \
  --attest-c1-outcomes-unseen --output "${AUTHORIZATION}" \
  "${task_inputs[@]}" "${scorers[@]}" "${evidence[@]}"
chmod 0444 "${AUTHORIZATION}"
sha256sum "${AUTHORIZATION}" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${STATE}" > "${AUTHORIZATION}.sha256"
chmod 0444 "${AUTHORIZATION}.sha256"
printf 'confirmation_authorization=%s\n' "${AUTHORIZATION}"
