#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e7p_sequence_cache.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e7p_sequence_cache.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/acid-alt-e6d-d2-be1fbf7803460e2e
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = be1fbf7803460e2e92bff190e6123f1237e794a4c9625ea836b90ec84c6d9750
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e7p-cache-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E7P-SEQUENCE-CACHE-PROTOCOL-2026-08-17.md
  ACID-ALTERNATIVE-E7-GOAL-CONDITIONED-DIFFUSION-PROPOSAL-DRAFT-2026-08-17.md
  build_goal_conditioned_action_sequence_cache.py
  test_goal_conditioned_action_sequence_cache.py
  run_gdp_cem_e7p_sequence_cache.slurm
  submit_gdp_cem_e7p_sequence_cache.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E7P-SEQUENCE-CACHE-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = 50690a07e2a2a949b0d0a9c5e43a8c4eb53b483780021ea20142031264de3299
bash -n "${staging}/run_gdp_cem_e7p_sequence_cache.slurm" "${staging}/submit_gdp_cem_e7p_sequence_cache.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" "${staging}/test_goal_conditioned_action_sequence_cache.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e7p-cache-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"

