#!/usr/bin/env bash
set -euo pipefail

snapshot=${1:?usage: submit_gdp_cem_e18.sh SNAPSHOT}
snapshot=$(cd "${snapshot}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
E15_TRAINING_ROOT=${ROOT}/experiments/gdp-cem-e15/development-run-20260825-ebd6109b/training
E17_RUN_ROOT=${ROOT}/experiments/gdp-cem-e17/development-run-20260827-9fb5a8c2
OLD_P2_ROOT=${ROOT}/experiments/gdp-cem-e14/development-run-20260823-99f92cbe/p2-manifests/33ae351f
source_hash=$(sha256sum "${snapshot}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
(cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -w "${snapshot}"
test "$(sha256sum "${snapshot}/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md" | cut -d' ' -f1)" = aff490f3f000c7d9b261632dcd3ccfc76a630b2f44e41f78832c3719607b8459
run_root=${ROOT}/experiments/gdp-cem-e18/development-run-20260827-${source_hash:0:8}
test ! -e "${run_root}"
mkdir -p "${run_root}"

input_job=$(sbatch --parsable \
  --export=ALL,SNAPSHOT="${snapshot}",E15_TRAINING_ROOT="${E15_TRAINING_ROOT}",E17_RUN_ROOT="${E17_RUN_ROOT}",OUTPUT_ROOT="${run_root}/input-audit" \
  "${snapshot}/run_gdp_cem_e18_input_audit.slurm")
p2_job=$(sbatch --parsable --dependency="afterok:${input_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",E17_RUN_ROOT="${E17_RUN_ROOT}",OLD_P2_ROOT="${OLD_P2_ROOT}",INPUT_AUDIT_ROOT="${run_root}/input-audit",OUTPUT_ROOT="${run_root}/p2-manifests" \
  "${snapshot}/run_gdp_cem_e18_p2_manifest.slurm")
evaluation_job=$(sbatch --parsable --dependency="afterok:${p2_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",E15_TRAINING_ROOT="${E15_TRAINING_ROOT}",E17_RUN_ROOT="${E17_RUN_ROOT}",INPUT_AUDIT_ROOT="${run_root}/input-audit",P2_ROOT="${run_root}/p2-manifests",EVALUATION_ROOT="${run_root}/evaluation" \
  "${snapshot}/run_gdp_cem_e18_evaluate.slurm")
analysis_job=$(sbatch --parsable --dependency="afterok:${evaluation_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",INPUT_AUDIT_ROOT="${run_root}/input-audit",P2_ROOT="${run_root}/p2-manifests",EVALUATION_ROOT="${run_root}/evaluation",OUTPUT_ROOT="${run_root}/analysis" \
  "${snapshot}/run_gdp_cem_e18_analyze.slurm")
printf 'run_root=%s\ninput_job=%s\np2_job=%s\nevaluation_job=%s\nanalysis_job=%s\n' \
  "${run_root}" "${input_job}" "${p2_job}" "${evaluation_job}" "${analysis_job}"
