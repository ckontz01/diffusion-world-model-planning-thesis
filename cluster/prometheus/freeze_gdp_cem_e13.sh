#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e13.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e13.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e11-1c52b60488373719
BASE_MANIFEST=1c52b60488373719017138bc33cef78fbc23551fe8efcb3637113a1d0b93c07e
PROTOCOL_SHA=65d56b613f12ad896c395e6feb4fc6d39f404bc802045369d0a88b638690af58
E12_MODEL_SHA=2cc5ae7f77efd1455b743cadb12dc133162aeeaed1878b250f8713767606b625
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e13-staging-20260822
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md
  gdp_cem_e12_specs.py gdp_cem_e12_prism_models.py gdp_cem_e12_prism_data.py
  preflight_gdp_cem_e12_stage_b.py test_gdp_cem_e12_prism_models.py
  gdp_cem_e13_specs.py
  create_gdp_cem_e13_d4_manifest.py test_create_gdp_cem_e13_d4_manifest.py
  evaluate_gdp_cem_e13_d4.py
  analyze_gdp_cem_e13_d4.py test_analyze_gdp_cem_e13_d4.py
  preflight_gdp_cem_e13.py
  run_gdp_cem_e13_preflight.slurm run_gdp_cem_e13_p1_smoke.slurm
  run_gdp_cem_e13_create_d4.slurm run_gdp_cem_e13_evaluate.slurm
  run_gdp_cem_e13_analyze.slurm submit_gdp_cem_e13.sh freeze_gdp_cem_e13.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E13-VELOCITY-VS-PRISM-DP-UNTOUCHED-D4-PROTOCOL-2026-08-22.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
test "$(sha256sum "${staging}/gdp_cem_e12_prism_models.py" | cut -d' ' -f1)" = "${E12_MODEL_SHA}"
if grep -R --line-number --fixed-strings --exclude=freeze_gdp_cem_e13.sh '__E13_' "${staging}"
then
  echo "unresolved E13 placeholder" >&2
  exit 2
fi
bash -n \
  "${staging}/run_gdp_cem_e13_preflight.slurm" \
  "${staging}/run_gdp_cem_e13_p1_smoke.slurm" \
  "${staging}/run_gdp_cem_e13_create_d4.slurm" \
  "${staging}/run_gdp_cem_e13_evaluate.slurm" \
  "${staging}/run_gdp_cem_e13_analyze.slurm" \
  "${staging}/submit_gdp_cem_e13.sh" \
  "${staging}/freeze_gdp_cem_e13.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
container_python() {
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
    PRISM_REFERENCE_ROOT="${ROOT}/downloads/prism-jepa-baa0eb95" \
    PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
    "${ENV_DIR}/bin/python" "$@"
}
container_python -m py_compile \
  "${staging}/gdp_cem_e12_prism_models.py" \
  "${staging}/gdp_cem_e13_specs.py" \
  "${staging}/create_gdp_cem_e13_d4_manifest.py" \
  "${staging}/evaluate_gdp_cem_e13_d4.py" \
  "${staging}/analyze_gdp_cem_e13_d4.py" \
  "${staging}/preflight_gdp_cem_e13.py"
container_python -m pytest -q "${staging}/test_gdp_cem_e12_prism_models.py"
container_python "${staging}/test_create_gdp_cem_e13_d4_manifest.py" >/dev/null
container_python "${staging}/test_analyze_gdp_cem_e13_d4.py" >/dev/null
printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  "upstream_source_manifest_sha256=${BASE_MANIFEST}" \
  "e12_prism_model_sha256=${E12_MODEL_SHA}" \
  'checks=python_compile,shell_syntax,e12_prism_equation_tests,synthetic_d4_manifest_selection,no_overwrite_publish,full_360_shard_synthetic_aggregate,array_bijection,seed_namespaces,start_cluster_bootstrap,information_barrier' \
  'd3_outcomes_read=false' \
  'd4_read=false' \
  'protected_p4_c1_i1_read=false' \
  > "${staging}/E13-STATIC-PREFLIGHT-PASSED.txt"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e13-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
