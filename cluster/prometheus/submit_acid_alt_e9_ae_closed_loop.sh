#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_acid_alt_e9_ae_closed_loop.sh IMMUTABLE_SNAPSHOT}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
evaluation=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_acid_alt_e9_ae_closed_loop.slurm")
evaluation=${evaluation%%;*}
[[ "${evaluation}" =~ ^[0-9]+$ ]] || exit 2
analysis=$(sbatch --parsable --dependency="afterok:${evaluation}" --export=ALL,SNAPSHOT="${SNAPSHOT}",E9_ARRAY_JOB_ID="${evaluation}" "${SNAPSHOT}/run_acid_alt_e9_ae_closed_loop_analyze.slurm")
analysis=${analysis%%;*}
[[ "${analysis}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\nevaluation_array_job=%s\nanalysis_job=%s\n' "${SNAPSHOT}" "${evaluation}" "${analysis}"

