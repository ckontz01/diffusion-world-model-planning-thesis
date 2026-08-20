#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_acid_alt_e6d_d2.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_acid_alt_e6d_d2.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/acid-alt-e6-d2-8af433ca7339f42c
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = 8af433ca7339f42c762b35b1f53d4e485926573531d66cd4bbe872f960240c1e
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.acid-alt-e6d-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E6D-ALL-ITERATIONS-MATCHED-CONTROLS-2026-08-17.md
  acid_alt_e6d_allgate.py evaluate_acid_alt_e6d_d2.py
  create_acid_alt_e6d_authorization.py analyze_acid_alt_e6d_d2.py test_acid_alt_e6d_analyzer.py
  run_acid_alt_e6d_authorize.slurm run_acid_alt_e6d_d2_closed_loop.slurm run_acid_alt_e6d_d2_analyze.slurm
  submit_acid_alt_e6d_d2.sh
)
for file in "${files[@]}"; do test -f "${source_root}/${file}"; cp "${source_root}/${file}" "${staging}/${file}"; done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E6D-ALL-ITERATIONS-MATCHED-CONTROLS-2026-08-17.md" | cut -d' ' -f1)" = 808f16435775c04b36862637efa200bc4eb47797089ac3f913be962035ed9fd4
for script in run_acid_alt_e6d_authorize.slurm run_acid_alt_e6d_d2_closed_loop.slurm run_acid_alt_e6d_d2_analyze.slurm submit_acid_alt_e6d_d2.sh; do bash -n "${staging}/${script}"; done
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" "${ENV_DIR}/bin/python" "${staging}/acid_alt_e6d_allgate.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" "${ENV_DIR}/bin/python" "${staging}/test_acid_alt_e6d_analyzer.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/acid-alt-e6d-d2-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
