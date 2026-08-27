#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e16_stage_c.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e16_stage_c.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e16-stage-b-77da6b995f2e8244
BASE_MANIFEST=77da6b995f2e824437b3e73a3ef723ec9261ba6ffe63677e039c031a346763c1
PROTOCOL_SHA=c308ca8117c6b0ac82c1df898e1f8e5e5f35f6af52685d27bc237a1b208df332
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e16-stage-c-staging-20260827
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  gdp_cem_e16_specs.py
  gdp_cem_e16_closed_loop.py
  create_gdp_cem_e16_p2_manifest.py
  create_gdp_cem_e16_stage_c_cells.py
  evaluate_gdp_cem_e16_stage_c.py
  test_gdp_cem_e16_closed_loop.py
  test_create_gdp_cem_e16_stage_c.py
  run_gdp_cem_e16_p2_manifest.slurm
  run_gdp_cem_e16_stage_c_evaluate.slurm
  freeze_gdp_cem_e16_stage_c.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E16-CONTINUATION-AWARE-DIRECT-VAD-DEVELOPMENT-PROTOCOL-2026-08-27.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n \
  "${staging}/run_gdp_cem_e16_p2_manifest.slurm" \
  "${staging}/run_gdp_cem_e16_stage_c_evaluate.slurm" \
  "${staging}/freeze_gdp_cem_e16_stage_c.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e16_specs.py" \
  "${staging}/gdp_cem_e16_closed_loop.py" \
  "${staging}/create_gdp_cem_e16_p2_manifest.py" \
  "${staging}/create_gdp_cem_e16_stage_c_cells.py" \
  "${staging}/evaluate_gdp_cem_e16_stage_c.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_gdp_cem_e16_models.py" \
  "${staging}/test_gdp_cem_e16_closed_loop.py" \
  "${staging}/test_create_gdp_cem_e16_stage_c.py"
"${ENV_DIR}/bin/python" "${staging}/create_gdp_cem_e16_stage_c_cells.py" \
  --output "${staging}/E16-STAGE-C-CELLS.tsv"
test "$(wc -l < "${staging}/E16-STAGE-C-CELLS.tsv")" -eq 337
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e16-stage-c-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
