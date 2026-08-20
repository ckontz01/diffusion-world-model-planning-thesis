#!/usr/bin/env bash
set -euo pipefail

repo_root=${1:?usage: freeze_acid_alt_v3_d2.sh REPO_ROOT OUTPUT_PARENT}
output_parent=${2:?usage: freeze_acid_alt_v3_d2.sh REPO_ROOT OUTPUT_PARENT}
source_root=${repo_root}/cluster/prometheus
core_root=${repo_root}/tmp/freeze-aa024-20260815/acid-alternative-core-v1-52acea39e4a1f6da/acid_alternative
diagnostics_root=${repo_root}/tmp/freeze-aa024-20260815/acid-alternative-diagnostics-v1-2a55d07d912bf1b6/acid_alternative_diagnostics
staging=${output_parent}/.acid-alt-v3-d2-staging-20260816
test -d "${core_root}"
test -d "${diagnostics_root}"
test ! -e "${staging}"
mkdir -p "${staging}/acid_alternative" "${staging}/acid_alternative_diagnostics"
cp -a "${core_root}/." "${staging}/acid_alternative/"
cp "${diagnostics_root}/__init__.py" "${staging}/acid_alternative_diagnostics/__init__.py"
for name in capture_candidate_pools.py execute_candidate_pools.py score_candidate_pools.py; do
  cp "${source_root}/acid_alternative_diagnostics/${name}" "${staging}/acid_alternative_diagnostics/${name}"
done

files=(
  ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md
  ACID-ALTERNATIVE-V3-AMENDMENT-1-2026-08-16.md
  ACID-ALTERNATIVE-V3-AMENDMENT-2-2026-08-16.md
  ACID-ALTERNATIVE-V3-AMENDMENT-3-2026-08-16.md
  acid_alt_d2_models.py
  preflight_acid_alt_v3.py
  create_acid_alt_d2_manifest.py
  train_residual_diffusion_multiseed_20260816.py
  aggregate_acid_alt_v3_p1_gate.py
  score_acid_alt_d2_task.py
  analyze_acid_alt_d2_stage_a.py
  evaluate_acid_alt_d2.py
  analyze_acid_alt_d2_stage_b.py
  run_acid_alt_v3_preflight.slurm
  run_acid_alt_v3_train_residual.slurm
  run_acid_alt_v3_p1_gate.slurm
  run_acid_alt_v3_create_d2.slurm
  run_acid_alt_v3_capture.slurm
  run_acid_alt_v3_execute.slurm
  run_acid_alt_v3_core_score.slurm
  run_acid_alt_v3_d2_score.slurm
  run_acid_alt_v3_stage_a_analyze.slurm
  run_acid_alt_v3_stage_b.slurm
  run_acid_alt_v3_stage_b_analyze.slurm
  submit_acid_alt_v3_stage_a.sh
  submit_acid_alt_v3_stage_b.sh
)
for name in "${files[@]}"; do cp "${source_root}/${name}" "${staging}/${name}"; done
cp "${repo_root}/tmp/train_residual_diffusion_pilot_20260816.py" "${staging}/train_residual_diffusion_pilot_20260816.py"
cp "${repo_root}/tmp/test_acid_alt_v3_analyzers.py" "${staging}/test_acid_alt_v3_analyzers.py"

test "$(sha256sum "${staging}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" | cut -d' ' -f1)" = c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb
test "$(sha256sum "${staging}/train_residual_diffusion_pilot_20260816.py" | cut -d' ' -f1)" = 871ebc12c4af778031155f78b060e017c7060775d3f2e32bb49dc986925a52ad
(
  cd "${staging}"
  find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256
  sha256sum -c SOURCE-MANIFEST.sha256
)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/acid-alt-v3-d2-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
