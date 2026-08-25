#!/usr/bin/env bash
set -euo pipefail

source_root=${1:?usage: freeze_gdp_cem_e15_training.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e15_training.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)

ROOT=/lustreFS/data/superworld/ckontzias/thesis
PROTOCOL_SHA=bcbe66b3b7b2635473d5bd98b3a450c5e136879f275ac3a0ddd6d4bdb254755b
test "${output_parent}" = "${ROOT}/snapshots"

staging=${output_parent}/.gdp-cem-e15-training-staging-20260825
test ! -e "${staging}"
mkdir -p "${staging}"
files=(
  ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md
  E15-BOUNDARY-AWARE-DATA-PREFLIGHT-SPEC-2026-08-25.md
  E15-BOUNDARY-AWARE-DATA-PREFLIGHT-RESULT-2026-08-25.md
  E15-IMPLEMENTATION-DECISIONS-1-2026-08-25.md
  gdp_cem_e14_models.py
  gdp_cem_e15_specs.py
  gdp_cem_e15_data.py
  gdp_cem_e15_models.py
  train_gdp_cem_e15_proposer.py
  preflight_gdp_cem_e15_training.py
  test_gdp_cem_e15_data.py
  test_gdp_cem_e15_models.py
  test_train_gdp_cem_e15_proposer.py
  run_gdp_cem_e15_training_preflight.slurm
  run_gdp_cem_e15_train.slurm
  freeze_gdp_cem_e15_training.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n "${staging}/run_gdp_cem_e15_training_preflight.slurm" "${staging}/run_gdp_cem_e15_train.slurm" "${staging}/freeze_gdp_cem_e15_training.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m py_compile \
  "${staging}/gdp_cem_e15_specs.py" \
  "${staging}/gdp_cem_e15_data.py" \
  "${staging}/gdp_cem_e15_models.py" \
  "${staging}/train_gdp_cem_e15_proposer.py" \
  "${staging}/preflight_gdp_cem_e15_training.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${staging}/test_gdp_cem_e15_data.py" \
  "${staging}/test_gdp_cem_e15_models.py" \
  "${staging}/test_train_gdp_cem_e15_proposer.py"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +

python3 - "${staging}/E15-TRAINING-STATIC-PREFLIGHT-PASSED.json" "${PROTOCOL_SHA}" <<'PY'
import json, sys
path, protocol_sha = sys.argv[1:]
with open(path, "x", encoding="utf-8") as stream:
    json.dump({
        "status": "passed",
        "protocol_sha256": protocol_sha,
        "checks": [
            "python_compile", "shell_syntax", "episode_derangement",
            "duration_mask", "trajectory_gmm_nll", "gmm_posterior",
            "smooth_bounded_decoder", "fixed_final_step_schedule"
        ],
        "training_started": False,
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
destination=${output_parent}/gdp-cem-e15-training-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
