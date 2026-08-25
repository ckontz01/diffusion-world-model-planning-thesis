#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e15_data_preflight.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e15_data_preflight.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
PREFLIGHT_SPEC_SHA=34ab12ba8f60fbcfd03361301fc69245719776c763aad88eb1162b520743d610
test "${output_parent}" = "${ROOT}/snapshots"

staging=${output_parent}/.gdp-cem-e15-data-staging-20260825
test ! -e "${staging}"
mkdir -p "${staging}"
files=(
  E15-BOUNDARY-AWARE-DATA-PREFLIGHT-SPEC-2026-08-25.md
  E15-IMPLEMENTATION-DECISIONS-1-2026-08-25.md
  gdp_cem_e15_data_specs.py
  build_gdp_cem_e15_bounded_cache.py
  test_build_gdp_cem_e15_bounded_cache.py
  run_gdp_cem_e15_data_preflight.slurm
  freeze_gdp_cem_e15_data_preflight.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/E15-BOUNDARY-AWARE-DATA-PREFLIGHT-SPEC-2026-08-25.md" | cut -d' ' -f1)" = "${PREFLIGHT_SPEC_SHA}"
bash -n "${staging}/run_gdp_cem_e15_data_preflight.slurm" "${staging}/freeze_gdp_cem_e15_data_preflight.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e15_data_specs.py" \
  "${staging}/build_gdp_cem_e15_bounded_cache.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_build_gdp_cem_e15_bounded_cache.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +

python3 - "${staging}/E15-DATA-STATIC-PREFLIGHT-PASSED.json" "${PREFLIGHT_SPEC_SHA}" <<'PY'
import json, sys
path, spec_sha = sys.argv[1:]
with open(path, "x", encoding="utf-8") as stream:
    json.dump({
        "status": "passed",
        "preflight_spec_sha256": spec_sha,
        "checks": [
            "python_compile",
            "shell_syntax",
            "episode_hash_split",
            "balanced_sampling",
            "sklearn_float32_transform",
            "bounded_inverse_finiteness",
        ],
        "model_training_performed": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
    }, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY

(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e15-data-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
