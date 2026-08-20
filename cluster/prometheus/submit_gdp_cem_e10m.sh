#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e10m.sh IMMUTABLE_SNAPSHOT}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sed -n 's/^status=//p' "${SNAPSHOT}/E10M-PREFLIGHT-PASSED.txt")" = passed
test "$(sed -n 's/^protocol_sha256=//p' "${SNAPSHOT}/E10M-PREFLIGHT-PASSED.txt")" = 02606573e4c7e4341814c76974ff2020f35fedcf2e8d1d08e531dd553e9787b9
training=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e10m_train.slurm")
training=${training%%;*}
[[ "${training}" =~ ^[0-9]+$ ]] || exit 2
evaluation=$(sbatch --parsable --dependency="afterok:${training}" --export=ALL,SNAPSHOT="${SNAPSHOT}",E10M_TRAIN_JOB_ID="${training}" "${SNAPSHOT}/run_gdp_cem_e10m_evaluate.slurm")
evaluation=${evaluation%%;*}
[[ "${evaluation}" =~ ^[0-9]+$ ]] || exit 2
analysis=$(sbatch --parsable --dependency="afterok:${evaluation}" --export=ALL,SNAPSHOT="${SNAPSHOT}",E10M_EVAL_JOB_ID="${evaluation}" "${SNAPSHOT}/run_gdp_cem_e10m_analyze.slurm")
analysis=${analysis%%;*}
[[ "${analysis}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\ntraining_array_job=%s\nevaluation_array_job=%s\nanalysis_job=%s\n' \
  "${SNAPSHOT}" "${training}" "${evaluation}" "${analysis}"
