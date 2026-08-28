#!/usr/bin/env bash
set -euo pipefail

snapshot=${1:?usage: submit_gdp_cem_e19.sh SNAPSHOT}
snapshot=$(cd "${snapshot}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
source_hash=$(sha256sum "${snapshot}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
(cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -w "${snapshot}"
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
run_root=${ROOT}/experiments/gdp-cem-e19/native-reproduction-run-20260828-${source_hash:0:8}
test ! -e "${run_root}"
mkdir -p "${run_root}"

prepare_job=$(sbatch --parsable \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_prepare.slurm")
release_job=$(sbatch --parsable --dependency="afterok:${prepare_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_release_audit.slurm")
overlap_job=$(sbatch --parsable --dependency="afterok:${prepare_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_data_overlap_audit.slurm")
runtime_job=$(sbatch --parsable --dependency="afterok:${release_job}:${overlap_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_runtime_preflight.slurm")
evaluation_job=$(sbatch --parsable --dependency="afterok:${runtime_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_evaluate.slurm")
analysis_job=$(sbatch --parsable --dependency="afterok:${evaluation_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_analyze.slurm")
printf 'run_root=%s\nprepare_job=%s\nrelease_job=%s\noverlap_job=%s\nruntime_job=%s\nevaluation_job=%s\nanalysis_job=%s\n' \
  "${run_root}" "${prepare_job}" "${release_job}" "${overlap_job}" \
  "${runtime_job}" "${evaluation_job}" "${analysis_job}"
