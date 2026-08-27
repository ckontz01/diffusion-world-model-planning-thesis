#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e17_adapter_preflight.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e17_adapter_preflight.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e16-diagnostics-3669dc328568ec48
BASE_MANIFEST=3669dc328568ec483a67149712bd2a7c118005a2f6251a74e0fe5af01f424f01
PROTOCOL_SHA=43ca72e15570c0aaeb26b5ce0f1e6a961d77fc7dd5b8d472938a8e8f00277c03
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)

staging=${output_parent}/.gdp-cem-e17-adapter-staging-20260827
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md
  gdp_cem_e17_specs.py
  gdp_cem_e17_models.py
  build_gdp_cem_e17_transition_state_cache.py
  train_gdp_cem_e17_transition_state_adapter.py
  analyze_gdp_cem_e17_transition_state_adapter.py
  test_gdp_cem_e17_models.py
  test_build_gdp_cem_e17_transition_state_cache.py
  test_train_gdp_cem_e17_transition_state_adapter.py
  test_analyze_gdp_cem_e17_transition_state_adapter.py
  run_gdp_cem_e17_transition_cache.slurm
  run_gdp_cem_e17_transition_state_adapter.slurm
  run_gdp_cem_e17_transition_state_adapter_analyze.slurm
  submit_gdp_cem_e17_adapter_preflight.sh
  freeze_gdp_cem_e17_adapter_preflight.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n \
  "${staging}/run_gdp_cem_e17_transition_cache.slurm" \
  "${staging}/run_gdp_cem_e17_transition_state_adapter.slurm" \
  "${staging}/run_gdp_cem_e17_transition_state_adapter_analyze.slurm" \
  "${staging}/submit_gdp_cem_e17_adapter_preflight.sh" \
  "${staging}/freeze_gdp_cem_e17_adapter_preflight.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e17_specs.py" \
  "${staging}/gdp_cem_e17_models.py" \
  "${staging}/build_gdp_cem_e17_transition_state_cache.py" \
  "${staging}/train_gdp_cem_e17_transition_state_adapter.py" \
  "${staging}/analyze_gdp_cem_e17_transition_state_adapter.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_gdp_cem_e17_models.py" \
  "${staging}/test_build_gdp_cem_e17_transition_state_cache.py" \
  "${staging}/test_train_gdp_cem_e17_transition_state_adapter.py" \
  "${staging}/test_analyze_gdp_cem_e17_transition_state_adapter.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
python3 - "${staging}/E17-ADAPTER-STATIC-PREFLIGHT-PASSED.json" "${PROTOCOL_SHA}" <<'PY'
import json, sys
path, protocol_sha = sys.argv[1:]
with open(path, "x", encoding="utf-8") as stream:
    json.dump({
        "status": "passed",
        "protocol_sha256": protocol_sha,
        "checks": [
            "python_compile", "shell_syntax", "transition_deduplication",
            "role_ordering", "action_conditioned_architecture",
            "final_checkpoint_before_validation", "copy_current_control",
            "task_and_tau_first_gate"
        ],
        "performance_metric_read": False,
        "p2_read": False,
        "d3_metric_read": False,
        "d4_metric_read": False,
        "d5_read": False,
        "protected_p3_p4_c1_i1_read": False,
        "claim_allowed": False,
    }, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e17-adapter-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
