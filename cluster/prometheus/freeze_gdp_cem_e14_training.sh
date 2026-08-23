#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e14_training.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e14_training.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
PROTOCOL_SHA=9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6
test "${output_parent}" = "${ROOT}/snapshots"

staging=${output_parent}/.gdp-cem-e14-training-staging-20260823
test ! -e "${staging}"
mkdir -p "${staging}"
files=(
  ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md
  ACID-ALTERNATIVE-E14-IMPLEMENTATION-DECISIONS-1-2026-08-23.md
  gdp_cem_e14_specs.py
  gdp_cem_e14_models.py
  gdp_cem_e14_data.py
  train_gdp_cem_e14_endpoint.py
  train_gdp_cem_e14_sage.py
  preflight_gdp_cem_e14_training.py
  create_gdp_cem_e14_training_manifests.py
  test_gdp_cem_e14_models.py
  test_gdp_cem_e14_training.py
  test_create_gdp_cem_e14_training_manifests.py
  run_gdp_cem_e14_training_preflight.slurm
  run_gdp_cem_e14_endpoint_train.slurm
  run_gdp_cem_e14_sage_train.slurm
  submit_gdp_cem_e14_training.sh
  freeze_gdp_cem_e14_training.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
if grep -R --line-number --fixed-strings --exclude=freeze_gdp_cem_e14_training.sh '__E14_' "${staging}"
then
  echo "unresolved E14 placeholder" >&2
  exit 2
fi
bash -n \
  "${staging}/run_gdp_cem_e14_training_preflight.slurm" \
  "${staging}/run_gdp_cem_e14_endpoint_train.slurm" \
  "${staging}/run_gdp_cem_e14_sage_train.slurm" \
  "${staging}/submit_gdp_cem_e14_training.sh" \
  "${staging}/freeze_gdp_cem_e14_training.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e14_specs.py" \
  "${staging}/gdp_cem_e14_models.py" \
  "${staging}/gdp_cem_e14_data.py" \
  "${staging}/train_gdp_cem_e14_endpoint.py" \
  "${staging}/train_gdp_cem_e14_sage.py" \
  "${staging}/preflight_gdp_cem_e14_training.py" \
  "${staging}/create_gdp_cem_e14_training_manifests.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_gdp_cem_e14_models.py" \
  "${staging}/test_gdp_cem_e14_training.py" \
  "${staging}/test_create_gdp_cem_e14_training_manifests.py"

PUSHT=/lustreFS/data/superworld/ckontzias/thesis/data/stablewm/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/e14-variable-cache-job-298993-0
CUBE=/lustreFS/data/superworld/ckontzias/thesis/data/stablewm/derived/acid-alternative-v1/cube/lewm-hf-b0747c5/e14-variable-cache-job-298993-1
test "$(sha256sum "${PUSHT}/cache.h5" | cut -d' ' -f1)" = ff102572c7eed39134002aa90af0bd324df1d1312522c994d19206ec5ac6bac9
test "$(sha256sum "${PUSHT}/manifest.json" | cut -d' ' -f1)" = 93a20e7d46e5142e2231630ae74caeec4638ad8aaeab95ef5b4cbd8513b90c54
test "$(sha256sum "${CUBE}/cache.h5" | cut -d' ' -f1)" = b7b4b63669d6eb05ccbc9cd7cc9a40e401f1a36ef0bdd9b61724dceb988b15f6
test "$(sha256sum "${CUBE}/manifest.json" | cut -d' ' -f1)" = 4385e22fcf199922d954a137817d283e829b345e66444a8644776ed592ef888e

find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  'checks=python_compile,shell_syntax,model_shapes,duration_masks,classifier_free_behavior,deterministic_velocity_sampling,independent_gmm_nll,gmm_sampling,parameter_counts,goal_derangement,masked_objective,manifest_bijection,cache_content_hashes' \
  'performance_outcome_read=false' \
  'd3_metric_read=false' \
  'd4_metric_read=false' \
  'd5_read=false' \
  'protected_p3_p4_c1_i1_read=false' \
  > "${staging}/E14-TRAINING-STATIC-PREFLIGHT-PASSED.txt"

(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e14-training-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"

