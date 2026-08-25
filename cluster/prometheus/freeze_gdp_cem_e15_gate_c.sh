#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e15_gate_c.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e15_gate_c.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e14-gate-c-9e47eeb2b957039e
BASE_MANIFEST=9e47eeb2b957039e7f952528b53dbaeca165120ee10b57f0691832907265e8ad
TRAINING=${ROOT}/snapshots/gdp-cem-e15-training-ebd6109b65528f6b
TRAINING_MANIFEST=ebd6109b65528f6b201c2de7deac29888a25e570f60d11ea9e6298374b61301c
OFFLINE=${ROOT}/snapshots/gdp-cem-e15-offline-d970a18e4921eb2c
OFFLINE_MANIFEST=d970a18e4921eb2c4d3d2ed7f6fdd295b583320b43fef1a88908000d82a8a22e
PROTOCOL_SHA=bcbe66b3b7b2635473d5bd98b3a450c5e136879f275ac3a0ddd6d4bdb254755b
test "${output_parent}" = "${ROOT}/snapshots"
for value in \
  "${BASE}|${BASE_MANIFEST}" \
  "${TRAINING}|${TRAINING_MANIFEST}" \
  "${OFFLINE}|${OFFLINE_MANIFEST}"; do
  directory=${value%%|*}
  expected=${value##*|}
  test "$(sha256sum "${directory}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${expected}"
  (cd "${directory}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done

staging=${output_parent}/.gdp-cem-e15-gate-c-staging-20260825
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
  gdp_cem_e14_specs.py
  gdp_cem_e14_data.py
  gdp_cem_e14_models.py
  gdp_cem_e14_closed_loop.py
  gdp_cem_latent_rollout.py
  evaluate_gdp_cem_e14_gate_c.py
  gdp_cem_e15_specs.py
  gdp_cem_e15_data.py
  gdp_cem_e15_models.py
  gdp_cem_e15_closed_loop.py
  create_gdp_cem_e15_gate_c_manifest.py
  evaluate_gdp_cem_e15_gate_c.py
  analyze_gdp_cem_e15_gate_c.py
  test_gdp_cem_e14_models.py
  test_gdp_cem_e14_closed_loop.py
  test_gdp_cem_e15_models.py
  test_gdp_cem_e15_closed_loop.py
  test_create_gdp_cem_e15_gate_c_manifest.py
  test_evaluate_gdp_cem_e15_gate_c.py
  test_analyze_gdp_cem_e15_gate_c.py
  run_gdp_cem_e15_gate_c_evaluate.slurm
  run_gdp_cem_e15_gate_c_analyze.slurm
  freeze_gdp_cem_e15_gate_c.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
grep -q --fixed-strings "${TRAINING_MANIFEST}" "${staging}/evaluate_gdp_cem_e15_gate_c.py"
grep -q --fixed-strings "${OFFLINE_MANIFEST}" "${staging}/evaluate_gdp_cem_e15_gate_c.py"
grep -q --fixed-strings "${OFFLINE_MANIFEST}" "${staging}/analyze_gdp_cem_e15_gate_c.py"
bash -n \
  "${staging}/run_gdp_cem_e15_gate_c_evaluate.slurm" \
  "${staging}/run_gdp_cem_e15_gate_c_analyze.slurm" \
  "${staging}/freeze_gdp_cem_e15_gate_c.sh"

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
  "${staging}/gdp_cem_e15_closed_loop.py" \
  "${staging}/create_gdp_cem_e15_gate_c_manifest.py" \
  "${staging}/evaluate_gdp_cem_e15_gate_c.py" \
  "${staging}/analyze_gdp_cem_e15_gate_c.py"
container_python -m pytest -q \
  "${staging}/test_gdp_cem_e14_models.py" \
  "${staging}/test_gdp_cem_e14_closed_loop.py" \
  "${staging}/test_gdp_cem_e15_models.py" \
  "${staging}/test_gdp_cem_e15_closed_loop.py" \
  "${staging}/test_create_gdp_cem_e15_gate_c_manifest.py" \
  "${staging}/test_evaluate_gdp_cem_e15_gate_c.py" \
  "${staging}/test_analyze_gdp_cem_e15_gate_c.py"
container_python "${staging}/create_gdp_cem_e15_gate_c_manifest.py" \
  --output "${staging}/E15-GATE-C-CELLS.tsv"
test "$(wc -l < "${staging}/E15-GATE-C-CELLS.tsv")" -eq 433
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
python3 - "${staging}/E15-GATE-C-STATIC-PREFLIGHT-PASSED.json" \
  "${PROTOCOL_SHA}" "${TRAINING_MANIFEST}" "${OFFLINE_MANIFEST}" <<'PY'
import json, sys
path, protocol_sha, training_sha, offline_sha = sys.argv[1:]
with open(path, "x", encoding="utf-8") as stream:
    json.dump({
        "status": "passed",
        "protocol_sha256": protocol_sha,
        "training_source_manifest_sha256": training_sha,
        "offline_source_manifest_sha256": offline_sha,
        "cell_count": 432,
        "checks": [
            "python_compile", "shell_syntax", "container_unit_tests",
            "task_first_bijective_cell_manifest", "paired_start_validation",
            "direct_gate_a_gate_b_revalidation", "one_stage_sage_population",
            "clustered_task_base_start_bootstrap", "registered_gate_boundaries",
            "synchronized_post_first_latency_estimator"
        ],
        "p2_metric_read": False,
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
destination=${output_parent}/gdp-cem-e15-gate-c-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
