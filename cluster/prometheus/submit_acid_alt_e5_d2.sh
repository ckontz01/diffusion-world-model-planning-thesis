#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: %s <immutable-e5-d2-snapshot>\n' "$0" >&2
  exit 2
fi
SNAPSHOT=$1
E4_D2A_SCORE_JOB_ID=297638
E4_P1_TRAIN_JOB_ID=297628
LEGACY_SHARED_JOB_ID=297538
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256 >/dev/null
)
submit() {
  sbatch --parsable "$@" | cut -d';' -f1
}
preflight=$(submit --export=ALL,SNAPSHOT="${SNAPSHOT}" \
  "${SNAPSHOT}/run_acid_alt_e5_d2_preflight.slurm")
scores=$(submit --dependency=afterok:${preflight} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",E4_D2A_SCORE_JOB_ID="${E4_D2A_SCORE_JOB_ID}",E4_P1_TRAIN_JOB_ID="${E4_P1_TRAIN_JOB_ID}",LEGACY_SHARED_JOB_ID="${LEGACY_SHARED_JOB_ID}" \
  "${SNAPSHOT}/run_acid_alt_e5_d2_score.slurm")
analysis=$(submit --dependency=afterok:${scores} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",E5_SCORE_JOB_ID="${scores}",E4_D2A_SCORE_JOB_ID="${E4_D2A_SCORE_JOB_ID}" \
  "${SNAPSHOT}/run_acid_alt_e5_d2_analyze.slurm")
printf 'snapshot=%s\npreflight_job=%s\ne5_score_array=%s\ne5_analysis_job=%s\n' \
  "${SNAPSHOT}" "${preflight}" "${scores}" "${analysis}"
