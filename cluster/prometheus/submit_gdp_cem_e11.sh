#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e11.sh IMMUTABLE_SNAPSHOT}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sed -n 's/^status=//p' "${SNAPSHOT}/E11-STATIC-PREFLIGHT-PASSED.txt")" = passed
test "$(sed -n 's/^protocol_sha256=//p' "${SNAPSHOT}/E11-STATIC-PREFLIGHT-PASSED.txt")" = 9b4bde9e2f69a7b92abaaf33f9db3016b8f61e82bedbe662a71a054cf3832ce0
ROOT=/lustreFS/data/superworld/ckontzias/thesis
test ! -e "${ROOT}/manifests/gdp-cem-e11-d3"
test ! -e "${ROOT}/results/acid-alternative/gdp-cem-e11-d3"
preflight=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e11_preflight.slurm")
preflight=${preflight%%;*}
[[ "${preflight}" =~ ^[0-9]+$ ]] || exit 2
smoke=$(sbatch --parsable --dependency="afterok:${preflight}" --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e11_p1_smoke.slurm")
smoke=${smoke%%;*}
[[ "${smoke}" =~ ^[0-9]+$ ]] || exit 2
manifest=$(sbatch --parsable --dependency="afterok:${smoke}" --export=ALL,SNAPSHOT="${SNAPSHOT}",PREFLIGHT_JOB_ID="${preflight}",SMOKE_JOB_ID="${smoke}" "${SNAPSHOT}/run_gdp_cem_e11_create_d3.slurm")
manifest=${manifest%%;*}
[[ "${manifest}" =~ ^[0-9]+$ ]] || exit 2
evaluation=$(sbatch --parsable --dependency="afterok:${manifest}" --export=ALL,SNAPSHOT="${SNAPSHOT}",MANIFEST_JOB_ID="${manifest}" "${SNAPSHOT}/run_gdp_cem_e11_evaluate.slurm")
evaluation=${evaluation%%;*}
[[ "${evaluation}" =~ ^[0-9]+$ ]] || exit 2
analysis=$(sbatch --parsable --dependency="afterok:${evaluation}" --export=ALL,SNAPSHOT="${SNAPSHOT}",EVALUATION_JOB_ID="${evaluation}" "${SNAPSHOT}/run_gdp_cem_e11_analyze.slurm")
analysis=${analysis%%;*}
[[ "${analysis}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\npreflight_job=%s\np1_smoke_job=%s\nd3_manifest_job=%s\nevaluation_array_job=%s\nanalysis_job=%s\n' \
  "${SNAPSHOT}" "${preflight}" "${smoke}" "${manifest}" "${evaluation}" "${analysis}"
