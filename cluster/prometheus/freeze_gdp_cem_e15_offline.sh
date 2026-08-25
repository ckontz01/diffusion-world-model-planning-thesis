#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e15_offline.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e15_offline.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e11-1c52b60488373719
BASE_MANIFEST=1c52b60488373719017138bc33cef78fbc23551fe8efcb3637113a1d0b93c07e
TRAINING=${ROOT}/snapshots/gdp-cem-e15-training-ebd6109b65528f6b
TRAINING_MANIFEST=ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c
PROTOCOL_SHA=bcbe66b3b7b2635473d5bd98b3a450c5e136879f275ac3a0ddd6d4bdb254755b
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
test "$(sha256sum "${TRAINING}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${TRAINING_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${TRAINING}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)

staging=${output_parent}/.gdp-cem-e15-offline-staging-20260825
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md
  E15-BOUNDARY-AWARE-DATA-PREFLIGHT-SPEC-2026-08-25.md
  E15-BOUNDARY-AWARE-DATA-PREFLIGHT-RESULT-2026-08-25.md
  E15-IMPLEMENTATION-DECISIONS-1-2026-08-25.md
  gdp_cem_e14_models.py
  gdp_cem_e15_specs.py
  gdp_cem_e15_data.py
  gdp_cem_e15_models.py
  evaluate_gdp_cem_e15_offline.py
  analyze_gdp_cem_e15_offline.py
  validate_gdp_cem_e15_gate_a.py
  test_gdp_cem_e15_models.py
  test_evaluate_gdp_cem_e15_offline.py
  test_analyze_gdp_cem_e15_offline.py
  run_gdp_cem_e15_offline_evaluate.slurm
  run_gdp_cem_e15_gate_a_validate.slurm
  run_gdp_cem_e15_offline_analyze.slurm
  freeze_gdp_cem_e15_offline.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
grep -q --fixed-strings "${TRAINING_MANIFEST}" "${staging}/evaluate_gdp_cem_e15_offline.py"
grep -q --fixed-strings \
  "d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e" \
  "${staging}/analyze_gdp_cem_e15_offline.py"
bash -n \
  "${staging}/run_gdp_cem_e15_offline_evaluate.slurm" \
  "${staging}/run_gdp_cem_e15_gate_a_validate.slurm" \
  "${staging}/run_gdp_cem_e15_offline_analyze.slurm" \
  "${staging}/freeze_gdp_cem_e15_offline.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
container_python() {
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
    "${ENV_DIR}/bin/python" "$@"
}
container_python -m py_compile \
  "${staging}/gdp_cem_e15_specs.py" \
  "${staging}/gdp_cem_e15_data.py" \
  "${staging}/gdp_cem_e15_models.py" \
  "${staging}/evaluate_gdp_cem_e15_offline.py" \
  "${staging}/analyze_gdp_cem_e15_offline.py" \
  "${staging}/validate_gdp_cem_e15_gate_a.py"
container_python -m pytest -q \
  "${staging}/test_gdp_cem_e15_models.py" \
  "${staging}/test_evaluate_gdp_cem_e15_offline.py" \
  "${staging}/test_analyze_gdp_cem_e15_offline.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
python3 - "${staging}/E15-OFFLINE-STATIC-PREFLIGHT-PASSED.json" "${PROTOCOL_SHA}" "${TRAINING_MANIFEST}" <<'PY'
import json, sys
path, protocol_sha, training_sha = sys.argv[1:]
with open(path, "x", encoding="utf-8") as stream:
    json.dump({
        "status": "passed",
        "protocol_sha256": protocol_sha,
        "training_source_manifest_sha256": training_sha,
        "checks": [
            "python_compile", "shell_syntax", "duration_mask",
            "trajectory_gmm_nll", "gmm_posterior",
            "direct_gmm_whole_trajectory_component_sampling",
            "smooth_bounded_decoder", "registered_boundary_metric_labels",
            "equal_cell_gate_aggregation", "vad_gate_positive_and_negative_cases",
            "gmm_structural_positive_case", "common_integrity_all_22_banks"
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
destination=${output_parent}/gdp-cem-e15-offline-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
