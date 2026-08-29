#!/usr/bin/env bash
set -euo pipefail

snapshot=${1:?usage: submit_gdp_cem_e19_discrepancy.sh SNAPSHOT}
snapshot=$(cd "${snapshot}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
source_hash=$(sha256sum "${snapshot}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
(cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -w "${snapshot}"
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
run_root=${ROOT}/experiments/gdp-cem-e19/discrepancy-diagnostic-run-20260829-${source_hash:0:8}
test ! -e "${run_root}"
mkdir -p "${run_root}"

sentinel_job=$(sbatch --parsable \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_discrepancy_sentinel.slurm")
comparison_job=$(sbatch --parsable --dependency="afterok:${sentinel_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_discrepancy_compare.slurm")
analysis_job=$(sbatch --parsable --dependency="afterok:${comparison_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e19_discrepancy_analyze.slurm")
printf 'run_root=%s\nsentinel_job=%s\ncomparison_job=%s\nanalysis_job=%s\n' \
  "${run_root}" "${sentinel_job}" "${comparison_job}" "${analysis_job}"
