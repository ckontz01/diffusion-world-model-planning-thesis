#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e16_stage_b.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e16_stage_b.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e16-diagnostics-3669dc328568ec48
BASE_MANIFEST=3669dc328568ec483a67149712bd2a7c118005a2f6251a74e0fe5af01f424f01
PROTOCOL_SHA=c308ca8117c6b0ac82c1df898e1f8e5e5f35f6af52685d27bc237a1b208df332
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e16-stage-b-staging-20260827
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  gdp_cem_e16_specs.py
  diagnose_gdp_cem_e16_one_continuation.py
  analyze_gdp_cem_e16_one_continuation.py
  test_diagnose_gdp_cem_e16_one_continuation.py
  run_gdp_cem_e16_one_continuation.slurm
  run_gdp_cem_e16_one_continuation_analyze.slurm
  freeze_gdp_cem_e16_stage_b.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E16-CONTINUATION-AWARE-DIRECT-VAD-DEVELOPMENT-PROTOCOL-2026-08-27.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n \
  "${staging}/run_gdp_cem_e16_one_continuation.slurm" \
  "${staging}/run_gdp_cem_e16_one_continuation_analyze.slurm" \
  "${staging}/freeze_gdp_cem_e16_stage_b.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e16_specs.py" \
  "${staging}/diagnose_gdp_cem_e16_one_continuation.py" \
  "${staging}/analyze_gdp_cem_e16_one_continuation.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_gdp_cem_e16_models.py" \
  "${staging}/test_diagnose_gdp_cem_e16_exact_banks.py" \
  "${staging}/test_diagnose_gdp_cem_e16_one_continuation.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e16-stage-b-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
