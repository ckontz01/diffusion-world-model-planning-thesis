#!/usr/bin/env bash
set -euo pipefail

repo_root=${1:?usage: freeze_acid_alt_e3_d2.sh REPO_ROOT OUTPUT_PARENT}
output_parent=${2:?usage: freeze_acid_alt_e3_d2.sh REPO_ROOT OUTPUT_PARENT}
source_root=${repo_root}/cluster/prometheus
v3_snapshot=${repo_root}/tmp/v3-freezes/acid-alt-v3-d2-2c8f890c31e9f5bf
staging=${output_parent}/.acid-alt-e3-d2-staging-20260816

test -d "${v3_snapshot}"
test "$(sha256sum "${v3_snapshot}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = \
  2c8f890c31e9f5bf5e8b6769ccc424d7cd565278c422405d507d1c702d3580ea
(
  cd "${v3_snapshot}"
  sha256sum -c SOURCE-MANIFEST.sha256
)
test ! -e "${staging}"
mkdir -p "${staging}"

cp -a "${v3_snapshot}/acid_alternative" "${staging}/acid_alternative"
cp "${v3_snapshot}/acid_alt_d2_models.py" "${staging}/acid_alt_d2_models.py"
cp "${v3_snapshot}/train_residual_diffusion_pilot_20260816.py" \
  "${staging}/train_residual_diffusion_pilot_20260816.py"
cp "${v3_snapshot}/SOURCE-MANIFEST.sha256" \
  "${staging}/V3-SOURCE-MANIFEST.sha256"

files=(
  ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-PROTOCOL-2026-08-16.md
  ACID-ALTERNATIVE-E3-AMENDMENT-1-2026-08-16.md
  create_acid_alt_e3_authorization.py
  preflight_acid_alt_e3.py
  evaluate_acid_alt_e3_d2.py
  analyze_acid_alt_e3_d2_closed_loop.py
  test_acid_alt_e3_analyzer.py
  run_acid_alt_e3_authorize.slurm
  run_acid_alt_e3_d2_closed_loop.slurm
  run_acid_alt_e3_d2_analyze.slurm
  submit_acid_alt_e3_d2.sh
)
for file in "${files[@]}"; do
  cp "${source_root}/${file}" "${staging}/${file}"
done

test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-PROTOCOL-2026-08-16.md" | cut -d' ' -f1)" = \
  c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0
test "$(sha256sum "${staging}/train_residual_diffusion_pilot_20260816.py" | cut -d' ' -f1)" = \
  871ebc12c4af778031155f78b060e017c7060775d3f2e32bb49dc986925a52ad

for script in \
  run_acid_alt_e3_authorize.slurm \
  run_acid_alt_e3_d2_closed_loop.slurm \
  run_acid_alt_e3_d2_analyze.slurm \
  submit_acid_alt_e3_d2.sh; do
  bash -n "${staging}/${script}"
done
python3 -m py_compile \
  "${staging}/create_acid_alt_e3_authorization.py" \
  "${staging}/preflight_acid_alt_e3.py" \
  "${staging}/evaluate_acid_alt_e3_d2.py" \
  "${staging}/analyze_acid_alt_e3_d2_closed_loop.py" \
  "${staging}/test_acid_alt_e3_analyzer.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -rf -- {} +

(
  cd "${staging}"
  find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum > SOURCE-MANIFEST.sha256
  sha256sum -c SOURCE-MANIFEST.sha256
)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/acid-alt-e3-d2-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' \
  "${destination}" "${manifest_hash}"
