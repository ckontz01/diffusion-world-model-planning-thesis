#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e7p_train.sh IMMUTABLE_SNAPSHOT [AFTER_JOB_ID]}
AFTER_JOB_ID=${2:-}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
dependency=()
if [[ -n "${AFTER_JOB_ID}" ]]; then
  [[ "${AFTER_JOB_ID}" =~ ^[0-9]+$ ]] || exit 2
  dependency+=(--dependency="afterany:${AFTER_JOB_ID}")
fi
result=$(sbatch --parsable "${dependency[@]}" --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e7p_train.slurm")
result=${result%%;*}
[[ "${result}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\ntraining_array_job=%s\n' "${SNAPSHOT}" "${result}"

