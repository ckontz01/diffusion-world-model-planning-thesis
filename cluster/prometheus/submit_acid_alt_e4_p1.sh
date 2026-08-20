#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'usage: %s <immutable-e4-snapshot>\n' "$0" >&2
  exit 2
fi
SNAPSHOT=$1
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256 >/dev/null
)
submit() {
  sbatch --parsable "$@" | cut -d';' -f1
}
preflight=$(submit --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_acid_alt_e4_preflight.slurm")
training=$(submit \
  --dependency=afterok:${preflight} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",PREFLIGHT_JOB_ID="${preflight}" \
  "${SNAPSHOT}/run_acid_alt_e4_p1_train.slurm")
gate=$(submit \
  --dependency=afterok:${training} \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",TRAIN_JOB_ID="${training}" \
  "${SNAPSHOT}/run_acid_alt_e4_p1_gate.slurm")
printf 'snapshot=%s\npreflight_job=%s\ntraining_array=%s\np1_gate_job=%s\n' \
  "${SNAPSHOT}" "${preflight}" "${training}" "${gate}"
