#!/usr/bin/env bash

# Submit the complete gated Le-WM development study. This script deliberately
# has no path that submits C1 confirmation.

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 CORE_SNAPSHOT DIAG_SNAPSHOT ORCH_SNAPSHOT" >&2
  exit 2
fi
CORE_SNAPSHOT="$1"
DIAG_SNAPSHOT="$2"
ORCH_SNAPSHOT="$3"
ROOT="${THESIS_ROOT:-/lustreFS/data/superworld/ckontzias/thesis}"
for required in "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256"; do test -f "${required}"; done
for snapshot in "${CORE_SNAPSHOT}" "${DIAG_SNAPSHOT}" "${ORCH_SNAPSHOT}"; do
  (cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done

submit() {
  local output
  output="$(sbatch --parsable "$@")"
  output="${output%%;*}"
  [[ "${output}" =~ ^[0-9]+$ ]] || { echo "unexpected sbatch response: ${output}" >&2; exit 2; }
  printf '%s' "${output}"
}

STATE_DIR="${ROOT}/submission-states/acid-alternative-v1"
mkdir -p "${STATE_DIR}"
STATE="${STATE_DIR}/d1-$(date -u +%Y%m%dT%H%M%SZ)-$$.tsv"
printf 'task\tstage\tjob_id\n' > "${STATE}"

diag_preflight="$(submit --export=ALL,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}" "${ORCH_SNAPSHOT}/run_acid_alt_diagnostic_preflight.slurm")"
printf 'all\tdiagnostic_preflight\t%s\n' "${diag_preflight}" >> "${STATE}"

declare -A prepare preflight latent transition pairs core controls reachability b0 acid_r0 gate d1 capture score execute audit sensitivity latency_cuda latency_episode
for task in pusht reacher cube; do
  prepare[${task}]="$(submit --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}" "${ORCH_SNAPSHOT}/run_prepare_acid_alt_task.slurm")"
  preflight[${task}]="$(submit --dependency=afterok:${prepare[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}" "${ORCH_SNAPSHOT}/run_acid_alt_task_preflight.slurm")"
  latent[${task}]="$(submit --dependency=afterok:${preflight[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}" "${ORCH_SNAPSHOT}/run_acid_alt_task_p1_latents.slurm")"
  transition[${task}]="$(submit --dependency=afterok:${latent[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",LATENT_JOB_ID="${latent[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_transition_cache.slurm")"
  pairs[${task}]="$(submit --dependency=afterok:${latent[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",LATENT_JOB_ID="${latent[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_reachability_pairs.slurm")"
  core[${task}]="$(submit --dependency=afterok:${transition[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",LATENT_JOB_ID="${latent[${task}]}",TRANSITION_JOB_ID="${transition[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_core_scorers.slurm")"
  controls[${task}]="$(submit --dependency=afterok:${transition[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",LATENT_JOB_ID="${latent[${task}]}",TRANSITION_JOB_ID="${transition[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_transition_controls.slurm")"
  reachability[${task}]="$(submit --dependency=afterok:${transition[${task}]}:${pairs[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",LATENT_JOB_ID="${latent[${task}]}",TRANSITION_JOB_ID="${transition[${task}]}",PAIR_JOB_ID="${pairs[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_reachability_heads.slurm")"
  b0[${task}]="$(submit --dependency=afterok:${preflight[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",PREFLIGHT_JOB_ID="${preflight[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_b0_r0.slurm")"
  acid_r0[${task}]="$(submit --dependency=afterok:${core[${task}]}:${preflight[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",SCORER_JOB_ID="${core[${task}]}",PREFLIGHT_JOB_ID="${preflight[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_a1_r0.slurm")"
  gate[${task}]="$(submit --dependency=afterok:${b0[${task}]}:${acid_r0[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",B0_JOB_ID="${b0[${task}]}",SCORER_JOB_ID="${core[${task}]}",ACID_EVAL_JOB_ID="${acid_r0[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_r0_gate.slurm")"
  d1[${task}]="$(submit --dependency=afterok:${gate[${task}]}:${reachability[${task}]}:${core[${task}]} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",CORE_SCORER_JOB_ID="${core[${task}]}",REACHABILITY_JOB_ID="${reachability[${task}]}",R0_GATE_JOB_ID="${gate[${task}]}",PREFLIGHT_JOB_ID="${preflight[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_d1_primary.slurm")"
  capture[${task}]="$(submit --dependency=afterok:${d1[${task}]}:${diag_preflight} --export=ALL,TASK="${task}",ANALYSIS_ROLE=D1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",PREFLIGHT_JOB_ID="${preflight[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_capture_candidates.slurm")"
  score[${task}]="$(submit --dependency=afterok:${capture[${task}]}:${core[${task}]}:${controls[${task}]}:${reachability[${task}]} --export=ALL,TASK="${task}",ANALYSIS_ROLE=D1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CAPTURE_JOB_ID="${capture[${task}]}",CORE_SCORER_JOB_ID="${core[${task}]}",REACHABILITY_JOB_ID="${reachability[${task}]}",CONTROL_JOB_ID="${controls[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_score_candidates.slurm")"
  execute[${task}]="$(submit --dependency=afterok:${capture[${task}]} --export=ALL,TASK="${task}",ANALYSIS_ROLE=D1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CAPTURE_JOB_ID="${capture[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_execute_candidates.slurm")"
  audit[${task}]="$(submit --dependency=afterok:${score[${task}]}:${execute[${task}]} --export=ALL,TASK="${task}",ANALYSIS_ROLE=D1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",SCORE_JOB_ID="${score[${task}]}",EXECUTION_JOB_ID="${execute[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_analyze_candidates.slurm")"
  sensitivity[${task}]="$(submit --dependency=afterok:${d1[${task}]} --export=ALL,TASK="${task}",ANALYSIS_ROLE=D1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",ORCH_SNAPSHOT="${ORCH_SNAPSHOT}",CORE_SCORER_JOB_ID="${core[${task}]}",REACHABILITY_JOB_ID="${reachability[${task}]}",PRIMARY_MATRIX_JOB_ID="${d1[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_sensitivity.slurm")"
  latency_cuda[${task}]="$(submit --dependency=afterok:${capture[${task}]}:${diag_preflight} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",CAPTURE_JOB_ID="${capture[${task}]}",CORE_SCORER_JOB_ID="${core[${task}]}",REACHABILITY_JOB_ID="${reachability[${task}]}",DIFFUSION_MODE=multi "${ORCH_SNAPSHOT}/run_acid_alt_task_latency_cuda.slurm")"
  latency_episode[${task}]="$(submit --dependency=afterok:${d1[${task}]}:${diag_preflight} --export=ALL,TASK="${task}",CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",CORE_SCORER_JOB_ID="${core[${task}]}",REACHABILITY_JOB_ID="${reachability[${task}]}" "${ORCH_SNAPSHOT}/run_acid_alt_task_latency_episode.slurm")"
  for stage in prepare preflight latent transition pairs core controls reachability b0 acid_r0 gate d1 capture score execute audit sensitivity latency_cuda latency_episode; do eval "job_id=\${${stage}[${task}]}"; printf '%s\t%s\t%s\n' "${task}" "${stage}" "${job_id}" >> "${STATE}"; done
done

closed_loop="$(submit --dependency=afterok:${d1[pusht]}:${d1[reacher]}:${d1[cube]}:${diag_preflight} --export=ALL,ROLE=development,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",PUSHT_MATRIX_JOB_ID="${d1[pusht]}",REACHER_MATRIX_JOB_ID="${d1[reacher]}",CUBE_MATRIX_JOB_ID="${d1[cube]}" "${ORCH_SNAPSHOT}/run_acid_alt_analyze_closed_loop.slurm")"
validation="$(submit --dependency=afterok:${core[pusht]}:${controls[pusht]}:${core[reacher]}:${controls[reacher]}:${core[cube]}:${controls[cube]}:${diag_preflight} --export=ALL,ANALYSIS_ROLE=D1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",PUSHT_CORE_SCORER_JOB_ID="${core[pusht]}",PUSHT_CONTROL_JOB_ID="${controls[pusht]}",REACHER_CORE_SCORER_JOB_ID="${core[reacher]}",REACHER_CONTROL_JOB_ID="${controls[reacher]}",CUBE_CORE_SCORER_JOB_ID="${core[cube]}",CUBE_CONTROL_JOB_ID="${controls[cube]}" "${ORCH_SNAPSHOT}/run_acid_alt_analyze_validation_all_tasks.slurm")"
mechanism="$(submit --dependency=afterok:${audit[pusht]}:${audit[reacher]}:${audit[cube]}:${diag_preflight} --export=ALL,ANALYSIS_ROLE=D1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",PUSHT_AUDIT_JOB_ID="${audit[pusht]}",REACHER_AUDIT_JOB_ID="${audit[reacher]}",CUBE_AUDIT_JOB_ID="${audit[cube]}" "${ORCH_SNAPSHOT}/run_acid_alt_aggregate_mechanism.slurm")"
sensitivity_analysis="$(submit --dependency=afterok:${sensitivity[pusht]}:${sensitivity[reacher]}:${sensitivity[cube]}:${diag_preflight} --export=ALL,ANALYSIS_ROLE=D1,CORE_SNAPSHOT="${CORE_SNAPSHOT}",DIAG_SNAPSHOT="${DIAG_SNAPSHOT}",PUSHT_SENSITIVITY_JOB_ID="${sensitivity[pusht]}",REACHER_SENSITIVITY_JOB_ID="${sensitivity[reacher]}",CUBE_SENSITIVITY_JOB_ID="${sensitivity[cube]}" "${ORCH_SNAPSHOT}/run_acid_alt_analyze_sensitivity.slurm")"
printf 'all\tclosed_loop_development\t%s\nall\tvalidation_development\t%s\nall\tmechanism\t%s\nall\tsensitivity_analysis\t%s\n' "${closed_loop}" "${validation}" "${mechanism}" "${sensitivity_analysis}" >> "${STATE}"
sha256sum "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${ORCH_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${STATE}" > "${STATE}.sha256"
printf 'submission_state=%s\n' "${STATE}"
column -t -s $'\t' "${STATE}" || true
