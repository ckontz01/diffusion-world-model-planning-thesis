#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_post_e14_boundary_diagnostic.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_post_e14_boundary_diagnostic.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e14-offline-bc27ec5c93dfae66
BASE_MANIFEST=bc27ec5c93dfae6681c149fd755d93742a0678583787bad7e3fcd43300d59cae
PROTOCOL_SHA=9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)

staging=${output_parent}/.gdp-post-e14-boundary-staging-r3-20260825
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  POST-E14-BOUNDARY-DIAGNOSTIC-PLAN-2026-08-25.md
  POST-E14-BOUNDARY-IMPLEMENTATION-DECISIONS-1-2026-08-25.md
  diagnose_gdp_cem_e14_boundaries.py
  analyze_gdp_cem_post_e14_boundary_diagnostic.py
  test_diagnose_gdp_cem_e14_boundaries.py
  test_analyze_gdp_cem_post_e14_boundary_diagnostic.py
  run_gdp_cem_post_e14_boundary_diagnostic.slurm
  run_gdp_cem_post_e14_boundary_analyze.slurm
  freeze_gdp_cem_post_e14_boundary_diagnostic.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n \
  "${staging}/run_gdp_cem_post_e14_boundary_diagnostic.slurm" \
  "${staging}/run_gdp_cem_post_e14_boundary_analyze.slurm" \
  "${staging}/freeze_gdp_cem_post_e14_boundary_diagnostic.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/diagnose_gdp_cem_e14_boundaries.py" \
  "${staging}/analyze_gdp_cem_post_e14_boundary_diagnostic.py" \
  "${staging}/test_diagnose_gdp_cem_e14_boundaries.py" \
  "${staging}/test_analyze_gdp_cem_post_e14_boundary_diagnostic.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_diagnose_gdp_cem_e14_boundaries.py" \
  "${staging}/test_analyze_gdp_cem_post_e14_boundary_diagnostic.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
printf '%s\n' \
  'status=passed' \
  "e14_protocol_sha256=${PROTOCOL_SHA}" \
  "upstream_e14_offline_source_manifest_sha256=${BASE_MANIFEST}" \
  'checks=python_compile,shell_syntax,boundary_mask_semantics,environment_to_planner_coordinate_transform,weighted_axis_aggregation,equal_condition_aggregation,full_row_distribution,equal_task_seed_aggregation' \
  'diagnostic_role=P1_development_artifact_diagnosis_only' \
  'd3_metric_read=false' \
  'd4_metric_read=false' \
  'd5_read=false' \
  'protected_p3_p4_c1_i1_read=false' \
  > "${staging}/POST-E14-BOUNDARY-STATIC-PREFLIGHT-PASSED.txt"
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-post-e14-boundary-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
