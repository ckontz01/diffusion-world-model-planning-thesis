#!/usr/bin/env bash
set -euo pipefail

snapshot=${1:?usage: submit_gdp_cem_e14_offline.sh SNAPSHOT TRAINING_RUN_ROOT TRAINING_JOB_ID}
training_root=${2:?usage: submit_gdp_cem_e14_offline.sh SNAPSHOT TRAINING_RUN_ROOT TRAINING_JOB_ID}
training_job=${3:?usage: submit_gdp_cem_e14_offline.sh SNAPSHOT TRAINING_RUN_ROOT TRAINING_JOB_ID}
snapshot=$(cd "${snapshot}" && pwd -P)
training_root=$(cd "${training_root}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
test ! -w "${snapshot}"
(cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest=${training_root}/manifests/endpoint-training.tsv
manifest_sha=$(sha256sum "${manifest}" | cut -d' ' -f1)
test "${manifest_sha}" = 56b9875529d2c5cc24467cecf91251ed52f3e2582cd1f49bc1046f1db80c7228
offline_root=${training_root}/offline
test ! -e "${offline_root}"
mkdir -p "${offline_root}"

smoke=$(sbatch --parsable --dependency=afterok:"${training_job}" \
  --export=ALL,SNAPSHOT="${snapshot}",TRAINING_RUN_ROOT="${training_root}",ENDPOINT_MANIFEST="${manifest}",ENDPOINT_MANIFEST_SHA256="${manifest_sha}",EVALUATION_ROOT="${offline_root}/smoke",MODE=smoke \
  "${snapshot}/run_gdp_cem_e14_offline_evaluate.slurm")
full=$(sbatch --parsable --dependency=afterok:"${smoke}" \
  --export=ALL,SNAPSHOT="${snapshot}",TRAINING_RUN_ROOT="${training_root}",ENDPOINT_MANIFEST="${manifest}",ENDPOINT_MANIFEST_SHA256="${manifest_sha}",EVALUATION_ROOT="${offline_root}/full",MODE=full \
  "${snapshot}/run_gdp_cem_e14_offline_evaluate.slurm")
analysis=$(sbatch --parsable --dependency=afterok:"${full}" \
  --export=ALL,SNAPSHOT="${snapshot}",ENDPOINT_MANIFEST="${manifest}",ENDPOINT_MANIFEST_SHA256="${manifest_sha}",FULL_EVALUATION_ROOT="${offline_root}/full",ANALYSIS_ROOT="${offline_root}/gate-b" \
  "${snapshot}/run_gdp_cem_e14_offline_analyze.slurm")
printf '%s\n' \
  "snapshot=${snapshot}" \
  "source_manifest_sha256=$(sha256sum "${snapshot}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" \
  "training_root=${training_root}" \
  "training_job=${training_job}" \
  "endpoint_manifest_sha256=${manifest_sha}" \
  "smoke_job=${smoke}" \
  "full_evaluation_job=${full}" \
  "gate_b_analysis_job=${analysis}" | tee "${offline_root}/SUBMISSION.txt"

