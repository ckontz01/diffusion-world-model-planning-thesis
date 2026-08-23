#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e14_offline.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e14_offline.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e11-1c52b60488373719
BASE_MANIFEST=1c52b60488373719017138bc33cef78fbc23551fe8efcb3637113a1d0b93c07e
TRAINING=${ROOT}/snapshots/gdp-cem-e14-training-99f92cbe3c735a99
TRAINING_MANIFEST=99f92cbe3c735a999866b52103241633ec80a7dffeca5217c07b0ec5590176cd
PROTOCOL_SHA=9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
test "$(sha256sum "${TRAINING}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${TRAINING_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${TRAINING}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)

staging=${output_parent}/.gdp-cem-e14-offline-staging-20260823
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md
  ACID-ALTERNATIVE-E14-IMPLEMENTATION-DECISIONS-1-2026-08-23.md
  gdp_cem_e14_specs.py
  gdp_cem_e14_models.py
  gdp_cem_e14_data.py
  train_gdp_cem_e14_endpoint.py
  train_gdp_cem_e14_sage.py
  evaluate_gdp_cem_e14_offline.py
  analyze_gdp_cem_e14_offline.py
  test_gdp_cem_e14_models.py
  test_gdp_cem_e14_training.py
  test_evaluate_gdp_cem_e14_offline.py
  test_analyze_gdp_cem_e14_offline.py
  run_gdp_cem_e14_offline_evaluate.slurm
  run_gdp_cem_e14_offline_analyze.slurm
  submit_gdp_cem_e14_offline.sh
  freeze_gdp_cem_e14_offline.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
grep -q --fixed-strings "${TRAINING_MANIFEST}" "${staging}/evaluate_gdp_cem_e14_offline.py"
if grep -R --line-number --fixed-strings --exclude=freeze_gdp_cem_e14_offline.sh '__E14_' "${staging}"
then
  echo "unresolved E14 placeholder" >&2
  exit 2
fi
bash -n \
  "${staging}/run_gdp_cem_e14_offline_evaluate.slurm" \
  "${staging}/run_gdp_cem_e14_offline_analyze.slurm" \
  "${staging}/submit_gdp_cem_e14_offline.sh" \
  "${staging}/freeze_gdp_cem_e14_offline.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
container_python() {
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
    "${ENV_DIR}/bin/python" "$@"
}
container_python -m py_compile \
  "${staging}/gdp_cem_e14_specs.py" \
  "${staging}/gdp_cem_e14_models.py" \
  "${staging}/gdp_cem_e14_data.py" \
  "${staging}/train_gdp_cem_e14_endpoint.py" \
  "${staging}/train_gdp_cem_e14_sage.py" \
  "${staging}/evaluate_gdp_cem_e14_offline.py" \
  "${staging}/analyze_gdp_cem_e14_offline.py"
container_python -m pytest -q \
  "${staging}/test_gdp_cem_e14_models.py" \
  "${staging}/test_gdp_cem_e14_training.py" \
  "${staging}/test_evaluate_gdp_cem_e14_offline.py" \
  "${staging}/test_analyze_gdp_cem_e14_offline.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  "upstream_e11_source_manifest_sha256=${BASE_MANIFEST}" \
  "training_source_manifest_sha256=${TRAINING_MANIFEST}" \
  'checks=python_compile,shell_syntax,model_shapes,strict_sampler_determinism,masked_objectives,equal_cell_aggregation,gaussian_nll,gate_b_positive_and_negative_synthetic_cases,full_manifest_and_hash_validation' \
  'd3_metric_read=false' \
  'd4_metric_read=false' \
  'd5_read=false' \
  'protected_p3_p4_c1_i1_read=false' \
  > "${staging}/E14-OFFLINE-STATIC-PREFLIGHT-PASSED.txt"
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e14-offline-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
