#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e12_stage_b.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e12_stage_b.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
PROTOCOL_SHA=08cbe26c3186f06d6731defc8fc66f63c2a55c1102f6d089f1e286176f9ed927
test "${output_parent}" = "${ROOT}/snapshots"
staging=${output_parent}/.gdp-cem-e12-stage-b-staging-20260820
test ! -e "${staging}"
mkdir -p "${staging}"
files=(
  ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md
  gdp_cem_e11_specs.py gdp_cem_e12_specs.py
  gdp_cem_e12_prism_models.py gdp_cem_e12_prism_data.py
  train_gdp_cem_e12_prism_head.py train_gdp_cem_e12_prism_dp.py
  preflight_gdp_cem_e12_stage_b.py collect_gdp_cem_e12_artifacts.py
  smoke_gdp_cem_e12_prism_dp_gpu.py
  test_gdp_cem_e12_prism_models.py
  run_gdp_cem_e12_stage_b_preflight.slurm
  run_gdp_cem_e12_stage_b_gpu_smoke.slurm
  run_gdp_cem_e12_prism_head_train.slurm
  run_gdp_cem_e12_prism_dp_train.slurm
  submit_gdp_cem_e12_stage_b.sh freeze_gdp_cem_e12_stage_b.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
if grep -R --line-number --fixed-strings --exclude=freeze_gdp_cem_e12_stage_b.sh '__E12_' "${staging}"
then
  echo "unresolved E12 placeholder" >&2
  exit 2
fi
bash -n \
  "${staging}/run_gdp_cem_e12_stage_b_preflight.slurm" \
  "${staging}/run_gdp_cem_e12_stage_b_gpu_smoke.slurm" \
  "${staging}/run_gdp_cem_e12_prism_head_train.slurm" \
  "${staging}/run_gdp_cem_e12_prism_dp_train.slurm" \
  "${staging}/submit_gdp_cem_e12_stage_b.sh" \
  "${staging}/freeze_gdp_cem_e12_stage_b.sh"
if grep -F 'mkdir -p "${OUT}"' \
  "${staging}/run_gdp_cem_e12_prism_head_train.slurm" \
  "${staging}/run_gdp_cem_e12_prism_dp_train.slurm"
then
  echo "training launcher pre-creates trainer-owned output directory" >&2
  exit 2
fi
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
container_python() {
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
    PRISM_REFERENCE_ROOT="${ROOT}/downloads/prism-jepa-baa0eb95" \
    PYTHONPATH="${staging}:${CODE}:${CODE}/third_party/lewm" \
    "${ENV_DIR}/bin/python" "$@"
}
container_python -m py_compile \
  "${staging}/gdp_cem_e11_specs.py" \
  "${staging}/gdp_cem_e12_specs.py" \
  "${staging}/gdp_cem_e12_prism_models.py" \
  "${staging}/gdp_cem_e12_prism_data.py" \
  "${staging}/train_gdp_cem_e12_prism_head.py" \
  "${staging}/train_gdp_cem_e12_prism_dp.py" \
  "${staging}/preflight_gdp_cem_e12_stage_b.py" \
  "${staging}/smoke_gdp_cem_e12_prism_dp_gpu.py" \
  "${staging}/collect_gdp_cem_e12_artifacts.py"
container_python -m pytest -q "${staging}/test_gdp_cem_e12_prism_models.py"
printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  'checks=python_compile,shell_syntax,public_prior_head_parity,public_beta_nll_parity,public_pog_parity,dp_parameter_count,ddim_determinism,p1_lineage,action_roundtrip' \
  'd3_outcomes_read=false' \
  'd4_read=false' \
  'protected_p4_c1_i1_read=false' \
  > "${staging}/E12-STAGE-B-STATIC-PREFLIGHT-PASSED.txt"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e12-stage-b-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
