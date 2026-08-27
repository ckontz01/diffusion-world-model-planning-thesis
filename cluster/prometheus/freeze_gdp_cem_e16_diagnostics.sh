#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e16_diagnostics.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e16_diagnostics.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e15-offline-d970a18e4921eb2c
BASE_MANIFEST=d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e
PROTOCOL_SHA=c308ca8117c6b0ac82c1df898e1f8e5e5f35f6af52685d27bc237a1b208df332
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)

staging=${output_parent}/.gdp-cem-e16-diagnostics-staging-20260827
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E16-CONTINUATION-AWARE-DIRECT-VAD-DEVELOPMENT-PROTOCOL-2026-08-27.md
  gdp_cem_e16_specs.py
  gdp_cem_e16_models.py
  train_gdp_cem_e16_state_adapter.py
  diagnose_gdp_cem_e16_exact_banks.py
  analyze_gdp_cem_e16_exact_banks.py
  test_gdp_cem_e16_models.py
  test_diagnose_gdp_cem_e16_exact_banks.py
  run_gdp_cem_e16_state_adapter.slurm
  run_gdp_cem_e16_exact_banks.slurm
  run_gdp_cem_e16_exact_banks_analyze.slurm
  freeze_gdp_cem_e16_diagnostics.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E16-CONTINUATION-AWARE-DIRECT-VAD-DEVELOPMENT-PROTOCOL-2026-08-27.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n \
  "${staging}/run_gdp_cem_e16_state_adapter.slurm" \
  "${staging}/run_gdp_cem_e16_exact_banks.slurm" \
  "${staging}/run_gdp_cem_e16_exact_banks_analyze.slurm" \
  "${staging}/freeze_gdp_cem_e16_diagnostics.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e16_specs.py" \
  "${staging}/gdp_cem_e16_models.py" \
  "${staging}/train_gdp_cem_e16_state_adapter.py" \
  "${staging}/diagnose_gdp_cem_e16_exact_banks.py" \
  "${staging}/analyze_gdp_cem_e16_exact_banks.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_gdp_cem_e16_models.py" \
  "${staging}/test_diagnose_gdp_cem_e16_exact_banks.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
python3 - "${staging}/E16-DIAGNOSTICS-STATIC-PREFLIGHT-PASSED.json" "${PROTOCOL_SHA}" <<'PY'
import json, sys
path, protocol_sha = sys.argv[1:]
with open(path, "x", encoding="utf-8") as stream:
    json.dump({
        "status": "passed",
        "protocol_sha256": protocol_sha,
        "checks": [
            "python_compile", "shell_syntax", "adapter_architecture",
            "best_two_continuation_score", "exact_bank_rank_metrics",
            "e15_replay_barrier", "task_first_stage_a_analysis"
        ],
        "performance_metric_read": False,
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
destination=${output_parent}/gdp-cem-e16-diagnostics-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
