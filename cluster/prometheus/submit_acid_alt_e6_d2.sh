#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_acid_alt_e6_d2.sh IMMUTABLE_SNAPSHOT}
ROOT=/lustreFS/data/superworld/ckontzias/thesis
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256 >/dev/null
)
submit() {
  local result
  result=$(sbatch --parsable "$@")
  result=${result%%;*}
  [[ "${result}" =~ ^[0-9]+$ ]] || { printf 'invalid sbatch result: %s\n' "${result}" >&2; exit 2; }
  printf '%s' "${result}"
}
authorization=$(submit --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_acid_alt_e6_authorize.slurm")
closed_loop=$(submit --dependency=afterok:${authorization} --export=ALL,SNAPSHOT="${SNAPSHOT}",AUTH_JOB_ID="${authorization}" "${SNAPSHOT}/run_acid_alt_e6_d2_closed_loop.slurm")
analysis=$(submit --dependency=afterok:${closed_loop} --export=ALL,SNAPSHOT="${SNAPSHOT}",AUTH_JOB_ID="${authorization}",E6_ARRAY_JOB_ID="${closed_loop}" "${SNAPSHOT}/run_acid_alt_e6_d2_analyze.slurm")
ledger=${ROOT}/results/acid-alternative/e6-d2-quantile/submissions/analysis-${analysis}.tsv
mkdir -p "$(dirname "${ledger}")"
printf 'stage\tjob_id\nauthorization\t%s\nclosed_loop_array_30\t%s\nanalysis\t%s\n' "${authorization}" "${closed_loop}" "${analysis}" > "${ledger}"
sha256sum "${ledger}" > "${ledger}.sha256"
printf 'snapshot=%s\nauthorization_job=%s\ne6_array_job=%s\ne6_analysis_job=%s\n' "${SNAPSHOT}" "${authorization}" "${closed_loop}" "${analysis}"
