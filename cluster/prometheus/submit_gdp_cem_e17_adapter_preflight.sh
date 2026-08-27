#!/usr/bin/env bash
set -euo pipefail

snapshot=${1:?usage: submit_gdp_cem_e17_adapter_preflight.sh SNAPSHOT RUN_ROOT}
run_root=${2:?usage: submit_gdp_cem_e17_adapter_preflight.sh SNAPSHOT RUN_ROOT}
snapshot=$(cd "${snapshot}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
E15_DATA_ROOT=${ROOT}/experiments/gdp-cem-e15/data-preflight-1b97e228
E16_RUN_ROOT=${ROOT}/experiments/gdp-cem-e16/development-run-20260827-3669dc32
test ! -w "${snapshot}"
(cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${run_root}"
mkdir -p "${run_root}"

cache_job=$(sbatch --parsable \
  --export=ALL,SNAPSHOT="${snapshot}",E15_DATA_ROOT="${E15_DATA_ROOT}",E16_RUN_ROOT="${E16_RUN_ROOT}",OUTPUT_ROOT="${run_root}/cache" \
  "${snapshot}/run_gdp_cem_e17_transition_cache.slurm")
model_job=$(sbatch --parsable --dependency=afterok:"${cache_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",CACHE_ROOT="${run_root}/cache",OUTPUT_ROOT="${run_root}/models" \
  "${snapshot}/run_gdp_cem_e17_transition_state_adapter.slurm")
analysis_job=$(sbatch --parsable --dependency=afterok:"${model_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",CACHE_ROOT="${run_root}/cache",MODEL_ROOT="${run_root}/models",OUTPUT_ROOT="${run_root}/analysis" \
  "${snapshot}/run_gdp_cem_e17_transition_state_adapter_analyze.slurm")

printf 'cache_job=%s\nmodel_job=%s\nanalysis_job=%s\nrun_root=%s\n' \
  "${cache_job}" "${model_job}" "${analysis_job}" "${run_root}"
