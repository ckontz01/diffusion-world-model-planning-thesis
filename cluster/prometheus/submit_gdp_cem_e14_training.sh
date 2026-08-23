#!/usr/bin/env bash
set -euo pipefail

snapshot=${1:?usage: submit_gdp_cem_e14_training.sh SNAPSHOT RUN_ROOT}
run_root=${2:?usage: submit_gdp_cem_e14_training.sh SNAPSHOT RUN_ROOT}
snapshot=$(cd "${snapshot}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
test ! -w "${snapshot}"
(cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${run_root}"
mkdir -p "${run_root}/manifests"

endpoint_manifest=${run_root}/manifests/endpoint-training.tsv
sage_manifest=${run_root}/manifests/sage-training.tsv
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${snapshot}" \
  "${ENV_DIR}/bin/python" "${snapshot}/create_gdp_cem_e14_training_manifests.py" \
  --endpoint-output "${endpoint_manifest}" --sage-output "${sage_manifest}"
endpoint_sha=$(sha256sum "${endpoint_manifest}" | cut -d' ' -f1)
sage_sha=$(sha256sum "${sage_manifest}" | cut -d' ' -f1)
sha256sum "${endpoint_manifest}" "${sage_manifest}" > "${run_root}/manifests/sha256.txt"

preflight=$(sbatch --parsable \
  --export=ALL,SNAPSHOT="${snapshot}",PREFLIGHT_ROOT="${run_root}/preflight" \
  "${snapshot}/run_gdp_cem_e14_training_preflight.slurm")
endpoint=$(sbatch --parsable --dependency=afterok:"${preflight}" \
  --export=ALL,SNAPSHOT="${snapshot}",TRAINING_MANIFEST="${endpoint_manifest}",TRAINING_MANIFEST_SHA256="${endpoint_sha}",RUN_ROOT="${run_root}" \
  "${snapshot}/run_gdp_cem_e14_endpoint_train.slurm")
sage_subgoal=$(sbatch --parsable --dependency=afterok:"${preflight}" \
  --export=ALL,SNAPSHOT="${snapshot}",SAGE_MANIFEST="${sage_manifest}",SAGE_MANIFEST_SHA256="${sage_sha}",RUN_ROOT="${run_root}",COMPONENT=subgoal \
  "${snapshot}/run_gdp_cem_e14_sage_train.slurm")
sage_option=$(sbatch --parsable --dependency=afterok:"${sage_subgoal}" \
  --export=ALL,SNAPSHOT="${snapshot}",SAGE_MANIFEST="${sage_manifest}",SAGE_MANIFEST_SHA256="${sage_sha}",RUN_ROOT="${run_root}",COMPONENT=option \
  "${snapshot}/run_gdp_cem_e14_sage_train.slurm")

printf '%s\n' \
  "snapshot=${snapshot}" \
  "source_manifest_sha256=$(sha256sum "${snapshot}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" \
  "run_root=${run_root}" \
  "endpoint_manifest_sha256=${endpoint_sha}" \
  "sage_manifest_sha256=${sage_sha}" \
  "preflight_job=${preflight}" \
  "endpoint_training_job=${endpoint}" \
  "sage_subgoal_job=${sage_subgoal}" \
  "sage_option_job=${sage_option}" | tee "${run_root}/SUBMISSION.txt"

