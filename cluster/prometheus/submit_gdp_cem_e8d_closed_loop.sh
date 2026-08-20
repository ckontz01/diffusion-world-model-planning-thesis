#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e8d_closed_loop.sh IMMUTABLE_SNAPSHOT}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sed -n 's/^status=//p' "${SNAPSHOT}/E8D-PREFLIGHT-PASSED.txt")" = passed
test "$(sed -n 's/^protocol_sha256=//p' "${SNAPSHOT}/E8D-PREFLIGHT-PASSED.txt")" = da502adde1bb53794e6552a185799ea7a19fdd557f0a927f2b1b395830f6a5ba
evaluation=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e8d_closed_loop.slurm")
evaluation=${evaluation%%;*}
[[ "${evaluation}" =~ ^[0-9]+$ ]] || exit 2
analysis=$(sbatch --parsable --dependency="afterok:${evaluation}" --export=ALL,SNAPSHOT="${SNAPSHOT}",E8D_ARRAY_JOB_ID="${evaluation}" "${SNAPSHOT}/run_gdp_cem_e8d_closed_loop_analyze.slurm")
analysis=${analysis%%;*}
[[ "${analysis}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\nevaluation_array_job=%s\nanalysis_job=%s\n' "${SNAPSHOT}" "${evaluation}" "${analysis}"
