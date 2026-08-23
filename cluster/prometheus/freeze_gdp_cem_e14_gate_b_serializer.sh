#!/usr/bin/env bash
set -euo pipefail

root=/lustreFS/data/superworld/ckontzias/thesis
source_dir=${1:?usage: freeze_gdp_cem_e14_gate_b_serializer.sh SOURCE_DIR}
output_parent=${root}/snapshots
files=(
  E14-GATE-B-SERIALIZATION-ERRATUM-2026-08-23.md
  run_gdp_cem_e14_gate_b_serializer.py
  run_gdp_cem_e14_gate_b_serializer.slurm
  test_run_gdp_cem_e14_gate_b_serializer.py
  freeze_gdp_cem_e14_gate_b_serializer.sh
)
for file in "${files[@]}"; do test -f "${source_dir}/${file}"; done
staging=$(mktemp -d "${output_parent}/.gdp-cem-e14-gate-b-json-staging-XXXXXX")
trap 'test ! -e "${staging}" || echo "preserved incomplete staging: ${staging}" >&2' EXIT
for file in "${files[@]}"; do cp "${source_dir}/${file}" "${staging}/${file}"; done
(
  cd "${staging}"
  sha256sum "${files[@]}" > SOURCE-MANIFEST.sha256
  sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null
)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e14-gate-b-json-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
