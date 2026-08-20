#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e8a_refinement.sh IMMUTABLE_SNAPSHOT}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
refinement=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e8a_refinement.slurm")
refinement=${refinement%%;*}
[[ "${refinement}" =~ ^[0-9]+$ ]] || exit 2
analysis=$(sbatch --parsable --dependency="afterok:${refinement}" --export=ALL,SNAPSHOT="${SNAPSHOT}",REFINEMENT_ARRAY_JOB_ID="${refinement}" "${SNAPSHOT}/run_gdp_cem_e8a_refinement_analyze.slurm")
analysis=${analysis%%;*}
[[ "${analysis}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\nrefinement_array_job=%s\nrefinement_analysis_job=%s\n' "${SNAPSHOT}" "${refinement}" "${analysis}"

