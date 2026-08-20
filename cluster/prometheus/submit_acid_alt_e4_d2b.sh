#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  printf 'usage: %s <immutable-e4-d2b-snapshot> <immutable-e4-d2a-snapshot>\n' "$0" >&2
  exit 2
fi
SNAPSHOT=$1
D2A_SNAPSHOT=$2
D2A_ANALYSIS_JOB_ID=297639
CONTROLS_JOB_ID=297637
P1_TRAIN_JOB_ID=297628
MANIFEST_JOB_ID=297535
for snapshot in "${SNAPSHOT}" "${D2A_SNAPSHOT}"; do
  test -d "${snapshot}"
  test ! -w "${snapshot}"
  (
    cd "${snapshot}"
    sha256sum --check SOURCE-MANIFEST.sha256 >/dev/null
  )
done
submit() {
  sbatch --parsable "$@" | cut -d';' -f1
}
preflight=$(submit \
  --dependency=afterok:${D2A_ANALYSIS_JOB_ID} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",D2A_SNAPSHOT="${D2A_SNAPSHOT}",D2A_ANALYSIS_JOB_ID="${D2A_ANALYSIS_JOB_ID}" \
  "${SNAPSHOT}/run_acid_alt_e4_d2b_preflight.slurm")
evaluations=$(submit \
  --dependency=afterok:${preflight} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",D2A_SNAPSHOT="${D2A_SNAPSHOT}",D2A_ANALYSIS_JOB_ID="${D2A_ANALYSIS_JOB_ID}",PREFLIGHT_JOB_ID="${preflight}",CONTROLS_JOB_ID="${CONTROLS_JOB_ID}",P1_TRAIN_JOB_ID="${P1_TRAIN_JOB_ID}",MANIFEST_JOB_ID="${MANIFEST_JOB_ID}" \
  "${SNAPSHOT}/run_acid_alt_e4_d2b_closed_loop.slurm")
analysis=$(submit \
  --dependency=afterok:${evaluations} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",D2A_SNAPSHOT="${D2A_SNAPSHOT}",D2A_ANALYSIS_JOB_ID="${D2A_ANALYSIS_JOB_ID}",EVAL_JOB_ID="${evaluations}" \
  "${SNAPSHOT}/run_acid_alt_e4_d2b_analyze.slurm")
printf 'snapshot=%s\nd2a_snapshot=%s\npreflight_job=%s\nevaluation_array=%s\nanalysis_job=%s\n' \
  "${SNAPSHOT}" "${D2A_SNAPSHOT}" "${preflight}" "${evaluations}" "${analysis}"

