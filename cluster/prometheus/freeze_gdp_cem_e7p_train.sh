#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e7p_train.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e7p_train.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e7p-cache-4a8350d8914aeaf4
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = 4a8350d8914aeaf40925f4df6e0aaaaa892a2bc95d8ee7c11fc56ad7ec33f18a
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e7p-train-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E7P-PROPOSAL-TRAINING-PROTOCOL-2026-08-17.md
  gdp_cem_models.py test_gdp_cem_models.py train_gdp_cem_proposal.py
  run_gdp_cem_e7p_train.slurm submit_gdp_cem_e7p_train.sh
)
for file in "${files[@]}"; do test -f "${source_root}/${file}"; cp "${source_root}/${file}" "${staging}/${file}"; done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E7P-PROPOSAL-TRAINING-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = b49e29adde3f1b0ce79c3a602f5a1af6a4159899a7941fb0f6cc30971bdb017b
bash -n "${staging}/run_gdp_cem_e7p_train.slurm" "${staging}/submit_gdp_cem_e7p_train.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" "${staging}/test_gdp_cem_models.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e7p-train-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"

