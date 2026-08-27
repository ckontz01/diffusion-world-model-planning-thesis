#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e18.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e18.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e17-adapter-9fb5a8c296feec81
BASE_MANIFEST=9fb5a8c296feec81c7982a79272e502216eaf91ad987b0e70c156cb2c5ad9fc1
PROTOCOL_SHA=aff490f3f000c7d9b261632dcd3ccfc76a630b2f44e41f78832c3719607b8459
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)

staging=${output_parent}/.gdp-cem-e18-staging-20260827
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md
  gdp_cem_e18_specs.py
  gdp_cem_e18_inputs.py
  gdp_cem_e18_runtime.py
  gdp_cem_e18_closed_loop.py
  create_gdp_cem_e18_cells.py
  create_gdp_cem_e18_p2_manifest.py
  validate_gdp_cem_e18_inputs.py
  evaluate_gdp_cem_e18.py
  analyze_gdp_cem_e18.py
  test_gdp_cem_e18_specs.py
  test_gdp_cem_e18_runtime.py
  test_gdp_cem_e18_closed_loop.py
  test_create_gdp_cem_e18_p2_manifest.py
  test_evaluate_gdp_cem_e18.py
  test_analyze_gdp_cem_e18.py
  run_gdp_cem_e18_input_audit.slurm
  run_gdp_cem_e18_p2_manifest.slurm
  run_gdp_cem_e18_evaluate.slurm
  run_gdp_cem_e18_analyze.slurm
  freeze_gdp_cem_e18.sh
  submit_gdp_cem_e18.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
python3 "${staging}/create_gdp_cem_e18_cells.py" --output "${staging}/E18-CELLS.tsv"
test "$(( $(wc -l < "${staging}/E18-CELLS.tsv") - 1 ))" = 240
bash -n \
  "${staging}/run_gdp_cem_e18_input_audit.slurm" \
  "${staging}/run_gdp_cem_e18_p2_manifest.slurm" \
  "${staging}/run_gdp_cem_e18_evaluate.slurm" \
  "${staging}/run_gdp_cem_e18_analyze.slurm" \
  "${staging}/freeze_gdp_cem_e18.sh" \
  "${staging}/submit_gdp_cem_e18.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e18_specs.py" \
  "${staging}/gdp_cem_e18_inputs.py" \
  "${staging}/gdp_cem_e18_runtime.py" \
  "${staging}/gdp_cem_e18_closed_loop.py" \
  "${staging}/create_gdp_cem_e18_cells.py" \
  "${staging}/create_gdp_cem_e18_p2_manifest.py" \
  "${staging}/validate_gdp_cem_e18_inputs.py" \
  "${staging}/evaluate_gdp_cem_e18.py" \
  "${staging}/analyze_gdp_cem_e18.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m pytest -q -p no:cacheprovider \
  "${staging}/test_gdp_cem_e18_specs.py" \
  "${staging}/test_gdp_cem_e18_runtime.py" \
  "${staging}/test_gdp_cem_e18_closed_loop.py" \
  "${staging}/test_create_gdp_cem_e18_p2_manifest.py" \
  "${staging}/test_evaluate_gdp_cem_e18.py" \
  "${staging}/test_analyze_gdp_cem_e18.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
python3 - "${staging}/E18-STATIC-PREFLIGHT-PASSED.json" "${PROTOCOL_SHA}" <<'PY'
import json, sys
path, protocol_sha = sys.argv[1:]
with open(path, "x", encoding="utf-8") as stream:
    json.dump({
        "status": "passed",
        "protocol_sha256": protocol_sha,
        "checks": [
            "python_compile", "shell_syntax", "exact_240_cell_registry",
            "action_conditioned_adapter_bridge", "best_two_continuation_score",
            "rollout_budget", "fresh_p2_selection", "task_first_aggregation",
            "task_base_start_cluster_bootstrap", "frozen_interpretation_rules"
        ],
        "performance_metric_read": False,
        "p2_outcome_read": False,
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
destination=${output_parent}/gdp-cem-e18-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
