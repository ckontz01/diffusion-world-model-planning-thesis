#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: %s <immutable-e4-d2a-snapshot>\n' "$0" >&2
  exit 2
fi
SNAPSHOT=$1
P1_GATE_JOB_ID=297629
P1_TRAIN_JOB_ID=297628
LEGACY_MANIFEST_JOB_ID=297535
LEGACY_SHARED_JOB_ID=297538
LEGACY_EXECUTION_JOB_ID=297537
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256 >/dev/null
)
submit() {
  sbatch --parsable "$@" | cut -d';' -f1
}
preflight=$(submit \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",P1_GATE_JOB_ID="${P1_GATE_JOB_ID}" \
  "${SNAPSHOT}/run_acid_alt_e4_d2a_preflight.slurm")
controls=$(submit \
  --dependency=afterok:${preflight} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",PREFLIGHT_JOB_ID="${preflight}" \
  "${SNAPSHOT}/run_acid_alt_e4_d2a_controls.slurm")
scores=$(submit \
  --dependency=afterok:${controls} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",CONTROLS_JOB_ID="${controls}",P1_GATE_JOB_ID="${P1_GATE_JOB_ID}",P1_TRAIN_JOB_ID="${P1_TRAIN_JOB_ID}",LEGACY_MANIFEST_JOB_ID="${LEGACY_MANIFEST_JOB_ID}",LEGACY_SHARED_JOB_ID="${LEGACY_SHARED_JOB_ID}",LEGACY_EXECUTION_JOB_ID="${LEGACY_EXECUTION_JOB_ID}" \
  "${SNAPSHOT}/run_acid_alt_e4_d2a_score.slurm")
analysis=$(submit \
  --dependency=afterok:${scores} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",P1_GATE_JOB_ID="${P1_GATE_JOB_ID}",D2A_SCORE_JOB_ID="${scores}" \
  "${SNAPSHOT}/run_acid_alt_e4_d2a_analyze.slurm")
printf 'snapshot=%s\npreflight_job=%s\ncontrols_array=%s\nd2a_score_array=%s\nd2a_analysis_job=%s\n' \
  "${SNAPSHOT}" "${preflight}" "${controls}" "${scores}" "${analysis}"
