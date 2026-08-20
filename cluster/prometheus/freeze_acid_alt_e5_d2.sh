#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_acid_alt_e5_d2.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_acid_alt_e5_d2.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
mkdir -p "${output_parent}"
output_parent=$(cd "${output_parent}" && pwd -P)
case "${output_parent}" in
  /lustreFS/data/superworld/ckontzias/thesis/snapshots) ;;
  *) printf 'unexpected E5 snapshot parent: %s\n' "${output_parent}" >&2; exit 2 ;;
esac
staging=${output_parent}/.acid-alt-e5-d2-staging-20260816
test ! -e "${staging}"
mkdir -p "${staging}"

files=(
  ACID-ALTERNATIVE-E5-COUNTERFACTUAL-DIFFUSION-DEVELOPMENT-2026-08-16.md
  acid_alt_e4_models.py
  acid_alt_e4_scoring.py
  train_acid_alt_e4_didm.py
  acid_alt_e5_counterfactual.py
  score_acid_alt_e5_d2_counterfactual.py
  analyze_acid_alt_e5_d2_counterfactual.py
  test_acid_alt_e4_models.py
  test_acid_alt_e4_scoring.py
  test_acid_alt_e5_counterfactual.py
  test_acid_alt_e5_d2_analyzer.py
  run_acid_alt_e5_d2_preflight.slurm
  run_acid_alt_e5_d2_score.slurm
  run_acid_alt_e5_d2_analyze.slurm
  submit_acid_alt_e5_d2.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done

for script in \
  run_acid_alt_e5_d2_preflight.slurm \
  run_acid_alt_e5_d2_score.slurm \
  run_acid_alt_e5_d2_analyze.slurm \
  submit_acid_alt_e5_d2.sh; do
  bash -n "${staging}/${script}"
done
project_root=/lustreFS/data/superworld/ckontzias/thesis
image=${project_root}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
env_dir=${project_root}/envs/hi-lewm-artifact-py311-cu121-swm006
test -f "${image}"
apptainer exec --cleanenv --bind "${project_root}:${project_root}" "${image}" \
  /usr/bin/env PYTHONNOUSERSITE=1 "${env_dir}/bin/python" -m py_compile \
  "${staging}/acid_alt_e4_models.py" \
  "${staging}/acid_alt_e4_scoring.py" \
  "${staging}/train_acid_alt_e4_didm.py" \
  "${staging}/acid_alt_e5_counterfactual.py" \
  "${staging}/score_acid_alt_e5_d2_counterfactual.py" \
  "${staging}/analyze_acid_alt_e5_d2_counterfactual.py" \
  "${staging}/test_acid_alt_e4_models.py" \
  "${staging}/test_acid_alt_e4_scoring.py" \
  "${staging}/test_acid_alt_e5_counterfactual.py" \
  "${staging}/test_acid_alt_e5_d2_analyzer.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +

(
  cd "${staging}"
  find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum > SOURCE-MANIFEST.sha256
  sha256sum --check SOURCE-MANIFEST.sha256
)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/acid-alt-e5-d2-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' \
  "${destination}" "${manifest_hash}"
