#!/usr/bin/env bash
set -euo pipefail

root=/lustreFS/data/superworld/ckontzias/thesis
source_dir=${1:?usage: freeze_gdp_cem_e14_gate_c.sh SOURCE_DIR}
output_parent=${root}/snapshots
protocol_sha=9909cd1357638ec4bcebd9a8c84a94f266d9a82e7003b902b7b2a0c65eea1be6
files=(
  ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md
  ACID-ALTERNATIVE-E14-IMPLEMENTATION-DECISIONS-1-2026-08-23.md
  gdp_cem_e14_specs.py
  gdp_cem_e14_models.py
  gdp_cem_e14_data.py
  gdp_cem_latent_rollout.py
  gdp_cem_e14_closed_loop.py
  normalize_gdp_cem_e14_training_paths.py
  create_gdp_cem_e14_gate_c_manifest.py
  evaluate_gdp_cem_e14_gate_c.py
  analyze_gdp_cem_e14_gate_c.py
  run_gdp_cem_e14_normalize_paths.slurm
  run_gdp_cem_e14_gate_c_manifest.slurm
  run_gdp_cem_e14_gate_c_evaluate.slurm
  run_gdp_cem_e14_gate_c_analyze.slurm
  test_gdp_cem_e14_models.py
  test_gdp_cem_e14_closed_loop.py
  test_normalize_gdp_cem_e14_training_paths.py
  test_evaluate_gdp_cem_e14_gate_c.py
  test_analyze_gdp_cem_e14_gate_c.py
)
for file in "${files[@]}"; do test -f "${source_dir}/${file}"; done
test "$(sha256sum "${source_dir}/${files[0]}" | cut -d' ' -f1)" = "${protocol_sha}"
staging=$(mktemp -d "${output_parent}/.gdp-cem-e14-gate-c-staging-XXXXXX")
trap 'test ! -e "${staging}" || echo "preserved incomplete staging: ${staging}" >&2' EXIT
for file in "${files[@]}"; do cp "${source_dir}/${file}" "${staging}/${file}"; done
(
  cd "${staging}"
  sha256sum "${files[@]}" > SOURCE-MANIFEST.sha256
  sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null
)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e14-gate-c-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
