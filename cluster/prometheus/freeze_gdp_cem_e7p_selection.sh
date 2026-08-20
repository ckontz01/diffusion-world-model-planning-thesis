#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e7p_selection.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e7p_selection.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e7p-train-e9ceb0caee33cb1b
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = e9ceb0caee33cb1b1e042373c84f7f58205b26d026979c85b5bf287fd85edba2
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e7p-selection-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E7P-PROPOSAL-SELECTION-PROTOCOL-2026-08-17.md
  ACID-ALTERNATIVE-E7P-PROPOSAL-SELECTION-IMPLEMENTATION-ERRATA-2026-08-17.md
  gdp_cem_models.py test_gdp_cem_models.py
  gdp_cem_latent_rollout.py test_gdp_cem_latent_rollout.py
  evaluate_gdp_cem_e7p_selection.py analyze_gdp_cem_e7p_selection.py
  run_gdp_cem_e7p_select.slurm run_gdp_cem_e7p_select_analyze.slurm
  submit_gdp_cem_e7p_selection.sh
)
for file in "${files[@]}"; do test -f "${source_root}/${file}"; cp "${source_root}/${file}" "${staging}/${file}"; done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E7P-PROPOSAL-SELECTION-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = 3c7ff146a43bb5d87e99d92dff0f9731f7ea4b186aedaec168db284ad744dbbc
bash -n "${staging}/run_gdp_cem_e7p_select.slurm" "${staging}/run_gdp_cem_e7p_select_analyze.slurm" "${staging}/submit_gdp_cem_e7p_selection.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
for test_script in test_gdp_cem_models.py test_gdp_cem_latent_rollout.py; do
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
    "${ENV_DIR}/bin/python" "${staging}/${test_script}"
done
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e7p-selection-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
