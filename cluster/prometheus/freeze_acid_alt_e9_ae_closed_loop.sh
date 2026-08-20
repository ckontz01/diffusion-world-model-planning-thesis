#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_acid_alt_e9_ae_closed_loop.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_acid_alt_e9_ae_closed_loop.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/acid-alt-v3-d2-2c8f890c31e9f5bf
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = 2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.acid-alt-e9-ae-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E9-AE-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md
  evaluate_acid_alt_d2.py analyze_acid_alt_e9_ae_closed_loop.py
  preflight_acid_alt_e9.py test_acid_alt_e9_analyzer.py
  test_acid_alt_e9_prerequisites.py
  run_acid_alt_e9_ae_closed_loop.slurm run_acid_alt_e9_ae_closed_loop_analyze.slurm
  submit_acid_alt_e9_ae_closed_loop.sh freeze_acid_alt_e9_ae_closed_loop.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E9-AE-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = ddabeed5f0d0cc5dd46b6d99f3e5f83f2ec122d09aac8beb48fc8a81965fa658
bash -n "${staging}/run_acid_alt_e9_ae_closed_loop.slurm" \
  "${staging}/run_acid_alt_e9_ae_closed_loop_analyze.slurm" \
  "${staging}/submit_acid_alt_e9_ae_closed_loop.sh" \
  "${staging}/freeze_acid_alt_e9_ae_closed_loop.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m py_compile "${staging}/evaluate_acid_alt_d2.py" \
  "${staging}/analyze_acid_alt_e9_ae_closed_loop.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" "${staging}/preflight_acid_alt_e9.py" \
  --root "${ROOT}" --trainer "${staging}/train_residual_diffusion_pilot_20260816.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" "${staging}/test_acid_alt_e9_analyzer.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${ROOT}/src/hi-lewm:${ROOT}/src/hi-lewm/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${staging}/test_acid_alt_e9_prerequisites.py" \
  --protocol "${staging}/ACID-ALTERNATIVE-E9-AE-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md" \
  --stage-a "${ROOT}/results/acid-alternative/v3-d2/stage-a/analysis/job-297565/summary.json"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/acid-alt-e9-ae-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
