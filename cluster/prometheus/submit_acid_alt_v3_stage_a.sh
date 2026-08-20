#!/usr/bin/env bash
set -euo pipefail
: "${SNAPSHOT:?run with immutable v3 snapshot path}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
submit() {
  local result
  result=$(sbatch --parsable "$@")
  [[ "${result}" =~ ^[0-9]+$ ]] || { printf 'invalid sbatch response: %q\n' "${result}" >&2; exit 2; }
  printf '%s' "${result}"
}

preflight=$(submit --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_acid_alt_v3_preflight.slurm")
training=$(submit --dependency=afterok:"${preflight}" --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_acid_alt_v3_train_residual.slurm")
p1_gate=$(submit --dependency=afterok:"${training}" --export=ALL,SNAPSHOT="${SNAPSHOT}",TRAIN_JOB_ID="${training}" "${SNAPSHOT}/run_acid_alt_v3_p1_gate.slurm")
d2_manifest=$(submit --dependency=afterok:"${p1_gate}" --export=ALL,SNAPSHOT="${SNAPSHOT}",P1_GATE_JOB_ID="${p1_gate}" "${SNAPSHOT}/run_acid_alt_v3_create_d2.slurm")
capture=$(submit --dependency=afterok:"${d2_manifest}" --export=ALL,SNAPSHOT="${SNAPSHOT}",MANIFEST_JOB_ID="${d2_manifest}" "${SNAPSHOT}/run_acid_alt_v3_capture.slurm")
execution=$(submit --dependency=afterok:"${capture}" --export=ALL,SNAPSHOT="${SNAPSHOT}",CAPTURE_JOB_ID="${capture}" "${SNAPSHOT}/run_acid_alt_v3_execute.slurm")
core_score=$(submit --dependency=afterok:"${capture}" --export=ALL,SNAPSHOT="${SNAPSHOT}",CAPTURE_JOB_ID="${capture}" "${SNAPSHOT}/run_acid_alt_v3_core_score.slurm")
d2_score=$(submit --dependency=afterok:"${execution}":"${core_score}" --export=ALL,SNAPSHOT="${SNAPSHOT}",TRAIN_JOB_ID="${training}",P1_GATE_JOB_ID="${p1_gate}",MANIFEST_JOB_ID="${d2_manifest}",CORE_SCORE_JOB_ID="${core_score}",EXECUTE_JOB_ID="${execution}" "${SNAPSHOT}/run_acid_alt_v3_d2_score.slurm")
stage_a=$(submit --dependency=afterok:"${d2_score}" --export=ALL,SNAPSHOT="${SNAPSHOT}",P1_GATE_JOB_ID="${p1_gate}",D2_SCORE_JOB_ID="${d2_score}" "${SNAPSHOT}/run_acid_alt_v3_stage_a_analyze.slurm")

ledger=${ROOT}/results/acid-alternative/v3-d2/submissions/stage-a-${stage_a}.tsv
mkdir -p "$(dirname "${ledger}")"
printf 'stage\tjob_id\npreflight\t%s\ntraining\t%s\np1_gate\t%s\nd2_manifest\t%s\ncapture\t%s\nexecution\t%s\ncore_score\t%s\nd2_score\t%s\nstage_a\t%s\n' \
  "${preflight}" "${training}" "${p1_gate}" "${d2_manifest}" "${capture}" "${execution}" "${core_score}" "${d2_score}" "${stage_a}" > "${ledger}"
sha256sum "${ledger}" > "${ledger}.sha256"
cat "${ledger}"
