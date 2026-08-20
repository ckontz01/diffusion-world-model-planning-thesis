#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e12_stage_b_audit.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e12_stage_b_audit.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
PROTOCOL_SHA=08cbe26c3186f06d6731defc8fc66f63c2a55c1102f6d089f1e286176f9ed927
test "${output_parent}" = "${ROOT}/snapshots"
staging=${output_parent}/.gdp-cem-e12-stage-b-audit-staging-20260820
test ! -e "${staging}"
mkdir -p "${staging}"
files=(
  ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md
  gdp_cem_e11_specs.py gdp_cem_e12_specs.py
  audit_gdp_cem_e12_stage_b.py run_gdp_cem_e12_stage_b_audit.slurm
  test_audit_gdp_cem_e12_stage_b.py
  submit_gdp_cem_e12_stage_b_audit.sh freeze_gdp_cem_e12_stage_b_audit.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n "${staging}/run_gdp_cem_e12_stage_b_audit.slurm" "${staging}/submit_gdp_cem_e12_stage_b_audit.sh" "${staging}/freeze_gdp_cem_e12_stage_b_audit.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e12_specs.py" "${staging}/audit_gdp_cem_e12_stage_b.py" \
  "${staging}/test_audit_gdp_cem_e12_stage_b.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m unittest -v test_audit_gdp_cem_e12_stage_b
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e12-stage-b-audit-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
