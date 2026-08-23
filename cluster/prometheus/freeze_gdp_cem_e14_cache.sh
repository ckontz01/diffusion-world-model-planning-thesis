#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e14_cache.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e14_cache.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
PROTOCOL_SHA=9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6
test "${output_parent}" = "${ROOT}/snapshots"

staging=${output_parent}/.gdp-cem-e14-cache-staging-20260823
test ! -e "${staging}"
mkdir -p "${staging}"
files=(
  ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md
  gdp_cem_e14_specs.py
  build_gdp_cem_e14_variable_cache.py
  test_build_gdp_cem_e14_variable_cache.py
  run_gdp_cem_e14_cache.slurm
  freeze_gdp_cem_e14_cache.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n "${staging}/run_gdp_cem_e14_cache.slurm" "${staging}/freeze_gdp_cem_e14_cache.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e14_specs.py" \
  "${staging}/build_gdp_cem_e14_variable_cache.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_build_gdp_cem_e14_variable_cache.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +

printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  'checks=python_compile,shell_syntax,synthetic_balanced_sampling,hdf5_row_order,masked_action_statistics' \
  'd3_metric_read=false' \
  'd4_metric_read=false' \
  'd5_read=false' \
  'protected_p3_p4_c1_i1_read=false' \
  > "${staging}/E14-CACHE-STATIC-PREFLIGHT-PASSED.txt"

(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e14-cache-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"

