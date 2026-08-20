#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_acid_alt_e6d_d2.sh IMMUTABLE_SNAPSHOT}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
submit() { local result; result=$(sbatch --parsable "$@"); result=${result%%;*}; [[ "${result}" =~ ^[0-9]+$ ]] || exit 2; printf '%s' "${result}"; }
auth=$(submit --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_acid_alt_e6d_authorize.slurm")
array=$(submit --dependency=afterok:${auth} --export=ALL,SNAPSHOT="${SNAPSHOT}",AUTH_JOB_ID="${auth}" "${SNAPSHOT}/run_acid_alt_e6d_d2_closed_loop.slurm")
analysis=$(submit --dependency=afterok:${array} --export=ALL,SNAPSHOT="${SNAPSHOT}",AUTH_JOB_ID="${auth}",E6D_ARRAY_JOB_ID="${array}" "${SNAPSHOT}/run_acid_alt_e6d_d2_analyze.slurm")
printf 'snapshot=%s\nauthorization_job=%s\ne6d_array_job=%s\ne6d_analysis_job=%s\n' "${SNAPSHOT}" "${auth}" "${array}" "${analysis}"
