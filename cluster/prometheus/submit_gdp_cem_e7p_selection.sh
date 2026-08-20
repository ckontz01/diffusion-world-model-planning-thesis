#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e7p_selection.sh IMMUTABLE_SNAPSHOT TRAINING_ARRAY_JOB_ID}
TRAINING_ARRAY_JOB_ID=${2:?usage: submit_gdp_cem_e7p_selection.sh IMMUTABLE_SNAPSHOT TRAINING_ARRAY_JOB_ID}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
[[ "${TRAINING_ARRAY_JOB_ID}" =~ ^[0-9]+$ ]] || exit 2
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
selection=$(sbatch --parsable --dependency="afterok:${TRAINING_ARRAY_JOB_ID}" --export=ALL,SNAPSHOT="${SNAPSHOT}",TRAINING_ARRAY_JOB_ID="${TRAINING_ARRAY_JOB_ID}" "${SNAPSHOT}/run_gdp_cem_e7p_select.slurm")
selection=${selection%%;*}
[[ "${selection}" =~ ^[0-9]+$ ]] || exit 2
analysis=$(sbatch --parsable --dependency="afterok:${selection}" --export=ALL,SNAPSHOT="${SNAPSHOT}",SELECTION_ARRAY_JOB_ID="${selection}" "${SNAPSHOT}/run_gdp_cem_e7p_select_analyze.slurm")
analysis=${analysis%%;*}
[[ "${analysis}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\nselection_array_job=%s\nselection_analysis_job=%s\n' "${SNAPSHOT}" "${selection}" "${analysis}"

