#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e8a_refinement.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e8a_refinement.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e7p-selection-9784aa64172a979f
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = 9784aa64172a979f22ac012d6d2abe2c27e6764e0e5b5251fd8298f04ae2c49f
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e8a-refinement-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E8A-GAUSSIAN-ANCHORED-DIFFUSION-REFINEMENT-PROTOCOL-2026-08-17.md
  gdp_cem_models.py test_gdp_cem_models.py
  evaluate_gdp_cem_e8a_refinement.py analyze_gdp_cem_e8a_refinement.py
  test_analyze_gdp_cem_e8a_refinement.py
  run_gdp_cem_e8a_refinement.slurm run_gdp_cem_e8a_refinement_analyze.slurm
  submit_gdp_cem_e8a_refinement.sh freeze_gdp_cem_e8a_refinement.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E8A-GAUSSIAN-ANCHORED-DIFFUSION-REFINEMENT-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = e6ad569e0313276bff2cf79835bcd53c4b1604113b34bacdb5004a4bae034141
bash -n "${staging}/run_gdp_cem_e8a_refinement.slurm" \
  "${staging}/run_gdp_cem_e8a_refinement_analyze.slurm" \
  "${staging}/submit_gdp_cem_e8a_refinement.sh" \
  "${staging}/freeze_gdp_cem_e8a_refinement.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_models.py" "${staging}/evaluate_gdp_cem_e8a_refinement.py" \
  "${staging}/analyze_gdp_cem_e8a_refinement.py"
for test_script in test_gdp_cem_models.py test_gdp_cem_latent_rollout.py test_analyze_gdp_cem_e8a_refinement.py; do
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
    "${ENV_DIR}/bin/python" "${staging}/${test_script}"
done
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e8a-refinement-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
