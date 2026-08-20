#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e12_stage_a.sh IMMUTABLE_SNAPSHOT}
ROOT=/lustreFS/data/superworld/ckontzias/thesis
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${ROOT}/results/acid-alternative/gdp-cem-e12/stage-a"
job=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e12_stage_a_native.slurm")
job=${job%%;*}
[[ "${job}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\nstage_a_array_job=%s\n' "${SNAPSHOT}" "${job}"
