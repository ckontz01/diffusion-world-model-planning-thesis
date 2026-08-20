#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e7p_sequence_cache.sh IMMUTABLE_SNAPSHOT}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
result=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e7p_sequence_cache.slurm")
result=${result%%;*}
[[ "${result}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\nsequence_cache_job=%s\n' "${SNAPSHOT}" "${result}"

