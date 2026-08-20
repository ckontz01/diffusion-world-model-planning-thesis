#!/usr/bin/env bash

# Submit the locked three-task C1 study from an immutable authorization and D1 state.

set -euo pipefail
if [[ $# -ne 5 ]]; then
  echo "usage: $0 CORE_SNAPSHOT DIAG_SNAPSHOT ORCH_SNAPSHOT C1_AUTHORIZATION D1_SUBMISSION_STATE" >&2
  exit 2
fi
CORE_SNAPSHOT="$1"; DIAG_SNAPSHOT="$2"; ORCH_SNAPSHOT="$3"; AUTHORIZATION="$4"; D1_STATE="$5"
ROOT="${THESIS_ROOT:-/lustreFS/data/superworld/ckontzias/thesis}"
for required in "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${AUTHORIZATION}" "${AUTHORIZATION}.sha256" "${D1_STATE}" "${D1_STATE}.sha256"; do test -f "${required}"; done
for snapshot in "${CORE_SNAPSHOT}" "${DIAG_SNAPSHOT}" "${ORCH_SNAPSHOT}"; do
  (cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done
sha256sum -c "${AUTHORIZATION}.sha256"
sha256sum -c "${D1_STATE}.sha256"
for location in "${ROOT}/results/acid-alternative/c1" "${ROOT}/results/acid-alternative/analysis/c1" "${ROOT}/results/acid-alternative/sensitivity/c1" "${ROOT}/results/acid-alternative/identification/c1"; do
  if [[ -d "${location}" ]] && find "${location}" -type f -print -quit | grep -q .; then
    echo "refusing duplicate C1 submission because files exist under ${location}" >&2
    exit 2
  fi
done
if [[ -d "${ROOT}/results/acid-alternative/diagnostics" ]] && find "${ROOT}/results/acid-alternative/diagnostics" -type f -path '*/c1-*/*' -print -quit | grep -q .; then
  echo "refusing duplicate C1 submission because C1 diagnostic files exist" >&2
  exit 2
fi
if [[ -d "${ROOT}/data/stablewm/derived/acid-alternative-v1" ]] && find "${ROOT}/data/stablewm/derived/acid-alternative-v1" -type f \( -path '*/i1-flat-latents-job-*/*' -o -path '*/i1-transition-cache-job-*/*' \) -print -quit | grep -q .; then
  echo "refusing duplicate C1 submission because derived I1 files exist" >&2
  exit 2
fi

submit() {
  local output
  output="$(sbatch --parsable "$@")"; output="${output%%;*}"
  [[ "${output}" =~ ^[0-9]+$ ]] || { echo "unexpected sbatch response: ${output}" >&2; exit 2; }
  printf '%s' "${output}"
}
lookup_job() {
  local task="$1" stage="$2" values
  values="$(awk -F '\t' -v task="${task}" -v stage="${stage}" 'NR > 1 && $1 == task && $2 == stage { print $3 }' "${D1_STATE}")"
  [[ "${values}" =~ ^[0-9]+$ ]] || { echo "missing or ambiguous ${task}/${stage}: ${values}" >&2; exit 2; }
  printf '%s' "${values}"
}

STATE_DIR="${ROOT}/submission-states/acid-alternative-v1"
mkdir -p "${STATE_DIR}"
STATE="${STATE_DIR}/c1-$(date -u +%Y%m%dT%H%M%SZ)-$$.tsv"
printf 'task\tstage\tjob_id\n' > "${STATE}"
diag_preflight="$(submit --export=ALL,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}" "${ORCH_SNAPSHOT}/run_acid_alt_diagnostic_preflight.slurm")"
printf 'all\tdiagnostic_preflight\t%s\n' "${diag_preflight}" >> "${STATE}"

declare -A primary i1_latent i1_cache identification capture score execute audit sensitivity
for task in pusht reacher cube; do
  core_job="$(lookup_job "${task}" core)"; control_job="$(lookup_job "${task}" controls)"; reachability_job="$(lookup_job "${task}" reachability)"
  preflight_job="$(lookup_job "${task}" preflight)"
  primary[${task}]="$(submit --dependency=afterok:${diag_preflight} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CORE_SCORER_JOB_ID="${core_job}",REACHABILITY_JOB_ID="${reachability_job}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_task_c1_primary.slurm")"
  printf '%s\tprimary\t%s\n' "${task}" "${primary[${task}]}" >> "${STATE}"
done

closed_loop="$(submit --dependency=afterok:${primary[pusht]}:${primary[reacher]}:${primary[cube]}:${diag_preflight} --export=ALL,ROLE=confirmation,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",PUSHT_MATRIX_JOB_ID="${primary[pusht]}",REACHER_MATRIX_JOB_ID="${primary[reacher]}",CUBE_MATRIX_JOB_ID="${primary[cube]}" "${ORCH_SNAPSHOT}/run_acid_alt_analyze_closed_loop.slurm")"
printf 'all\tclosed_loop_confirmation\t%s\n' "${closed_loop}" >> "${STATE}"

for task in pusht reacher cube; do
  core_job="$(lookup_job "${task}" core)"; control_job="$(lookup_job "${task}" controls)"; reachability_job="$(lookup_job "${task}" reachability)"
  training_transition_job="$(lookup_job "${task}" transition)"; preflight_job="$(lookup_job "${task}" preflight)"
  i1_latent[${task}]="$(submit --dependency=afterok:${closed_loop} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_task_i1_latents.slurm")"
  i1_cache[${task}]="$(submit --dependency=afterok:${i1_latent[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",I1_LATENT_JOB_ID="${i1_latent[${task}]}",TRAINING_TRANSITION_JOB_ID="${training_transition_job}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_task_i1_transition_cache.slurm")"
  identification[${task}]="$(submit --dependency=afterok:${i1_cache[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CORE_SCORER_JOB_ID="${core_job}",CONTROL_JOB_ID="${control_job}",I1_LATENT_JOB_ID="${i1_latent[${task}]}",I1_TRANSITION_JOB_ID="${i1_cache[${task}]}",TRAINING_TRANSITION_JOB_ID="${training_transition_job}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_task_c1_identification.slurm")"
  capture[${task}]="$(submit --dependency=afterok:${closed_loop}:${diag_preflight} --export=ALL,TASK="${task}",ANALYSIS_ROLE=C1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",PREFLIGHT_JOB_ID="${preflight_job}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_task_capture_candidates.slurm")"
  score[${task}]="$(submit --dependency=afterok:${capture[${task}]} --export=ALL,TASK="${task}",ANALYSIS_ROLE=C1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CAPTURE_JOB_ID="${capture[${task}]}",CORE_SCORER_JOB_ID="${core_job}",REACHABILITY_JOB_ID="${reachability_job}",CONTROL_JOB_ID="${control_job}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_task_score_candidates.slurm")"
  execute[${task}]="$(submit --dependency=afterok:${capture[${task}]} --export=ALL,TASK="${task}",ANALYSIS_ROLE=C1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CAPTURE_JOB_ID="${capture[${task}]}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_task_execute_candidates.slurm")"
  audit[${task}]="$(submit --dependency=afterok:${score[${task}]}:${execute[${task}]} --export=ALL,TASK="${task}",ANALYSIS_ROLE=C1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",SCORE_JOB_ID="${score[${task}]}",EXECUTION_JOB_ID="${execute[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_analyze_candidates.slurm")"
  printf '%s\ti1_latent\t%s\n%s\ti1_transition\t%s\n%s\tidentification\t%s\n%s\tcapture\t%s\n%s\tscore\t%s\n%s\texecute\t%s\n%s\taudit\t%s\n' "${task}" "${i1_latent[${task}]}" "${task}" "${i1_cache[${task}]}" "${task}" "${identification[${task}]}" "${task}" "${capture[${task}]}" "${task}" "${score[${task}]}" "${task}" "${execute[${task}]}" "${task}" "${audit[${task}]}" >> "${STATE}"
done

validation="$(submit --dependency=afterok:${identification[pusht]}:${identification[reacher]}:${identification[cube]}:${diag_preflight} --export=ALL,ANALYSIS_ROLE=C1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",PUSHT_IDENTIFICATION_JOB_ID="${identification[pusht]}",REACHER_IDENTIFICATION_JOB_ID="${identification[reacher]}",CUBE_IDENTIFICATION_JOB_ID="${identification[cube]}" "${ORCH_SNAPSHOT}/run_acid_alt_analyze_validation_all_tasks.slurm")"
mechanism="$(submit --dependency=afterok:${audit[pusht]}:${audit[reacher]}:${audit[cube]}:${diag_preflight} --export=ALL,ANALYSIS_ROLE=C1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",PUSHT_AUDIT_JOB_ID="${audit[pusht]}",REACHER_AUDIT_JOB_ID="${audit[reacher]}",CUBE_AUDIT_JOB_ID="${audit[cube]}" "${ORCH_SNAPSHOT}/run_acid_alt_aggregate_mechanism.slurm")"
claim="$(submit --dependency=afterok:${closed_loop}:${validation}:${mechanism} --export=ALL,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",CLOSED_LOOP_JOB_ID="${closed_loop}",VALIDATION_JOB_ID="${validation}",MECHANISM_JOB_ID="${mechanism}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_assemble_c1_claim.slurm")"
printf 'all\tvalidation_confirmation\t%s\nall\tmechanism_confirmation\t%s\nall\tclaim_decision\t%s\n' "${validation}" "${mechanism}" "${claim}" >> "${STATE}"

for task in pusht reacher cube; do
  core_job="$(lookup_job "${task}" core)"; reachability_job="$(lookup_job "${task}" reachability)"
  sensitivity[${task}]="$(submit --dependency=afterok:${claim} --export=ALL,TASK="${task}",ANALYSIS_ROLE=C1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CORE_SCORER_JOB_ID="${core_job}",REACHABILITY_JOB_ID="${reachability_job}",PRIMARY_MATRIX_JOB_ID="${primary[${task}]}",PRIMARY_ANALYSIS_JOB_ID="${closed_loop}",CONFIRMATION_AUTHORIZATION="${AUTHORIZATION}" "${ORCH_SNAPSHOT}/run_acid_alt_task_sensitivity.slurm")"
  printf '%s\tsensitivity\t%s\n' "${task}" "${sensitivity[${task}]}" >> "${STATE}"
done
sensitivity_analysis="$(submit --dependency=afterok:${sensitivity[pusht]}:${sensitivity[reacher]}:${sensitivity[cube]}:${diag_preflight} --export=ALL,ANALYSIS_ROLE=C1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",PUSHT_SENSITIVITY_JOB_ID="${sensitivity[pusht]}",REACHER_SENSITIVITY_JOB_ID="${sensitivity[reacher]}",CUBE_SENSITIVITY_JOB_ID="${sensitivity[cube]}" "${ORCH_SNAPSHOT}/run_acid_alt_analyze_sensitivity.slurm")"
printf 'all\tsensitivity_analysis\t%s\n' "${sensitivity_analysis}" >> "${STATE}"
sha256sum "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${AUTHORIZATION}" "${D1_STATE}" "${STATE}" > "${STATE}.sha256"
printf 'submission_state=%s\n' "${STATE}"
column -t -s $'\t' "${STATE}" || true
