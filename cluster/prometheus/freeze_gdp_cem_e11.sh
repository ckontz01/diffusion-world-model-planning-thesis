#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e11.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e11.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e10m-3231a9d92fc7f6eb
BASE_MANIFEST=3231a9d92fc7f6ebf333a7a361adafd40c43eb6240fa377710d9eaaa48b12c65
PROTOCOL_SHA=9b4bde9e2f69a7b92abaaf33f9db3016b8f61e82bedbe662a71a054cf3832ce0
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e11-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md
  gdp_cem_models.py test_gdp_cem_models.py gdp_cem_e11_specs.py
  evaluate_gdp_cem_e8d_closed_loop.py
  create_gdp_cem_e11_d3_manifest.py test_create_gdp_cem_e11_d3_manifest.py
  evaluate_gdp_cem_e11_d3.py
  analyze_gdp_cem_e11_d3.py test_analyze_gdp_cem_e11_d3.py
  preflight_gdp_cem_e11.py smoke_gdp_cem_e11_p1.py
  run_gdp_cem_e11_preflight.slurm run_gdp_cem_e11_p1_smoke.slurm
  run_gdp_cem_e11_create_d3.slurm run_gdp_cem_e11_evaluate.slurm
  run_gdp_cem_e11_analyze.slurm submit_gdp_cem_e11.sh
  freeze_gdp_cem_e11.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
if grep -R --line-number --fixed-strings --exclude=freeze_gdp_cem_e11.sh '__E11_' "${staging}"
then
  echo "unresolved E11 placeholder" >&2
  exit 2
fi
bash -n \
  "${staging}/run_gdp_cem_e11_preflight.slurm" \
  "${staging}/run_gdp_cem_e11_p1_smoke.slurm" \
  "${staging}/run_gdp_cem_e11_create_d3.slurm" \
  "${staging}/run_gdp_cem_e11_evaluate.slurm" \
  "${staging}/run_gdp_cem_e11_analyze.slurm" \
  "${staging}/submit_gdp_cem_e11.sh" \
  "${staging}/freeze_gdp_cem_e11.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
container_python() {
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
    "${ENV_DIR}/bin/python" "$@"
}
container_python -m py_compile \
  "${staging}/gdp_cem_models.py" \
  "${staging}/gdp_cem_e11_specs.py" \
  "${staging}/create_gdp_cem_e11_d3_manifest.py" \
  "${staging}/evaluate_gdp_cem_e11_d3.py" \
  "${staging}/analyze_gdp_cem_e11_d3.py" \
  "${staging}/preflight_gdp_cem_e11.py" \
  "${staging}/smoke_gdp_cem_e11_p1.py"
container_python "${staging}/test_gdp_cem_models.py"
container_python "${staging}/test_gdp_cem_latent_rollout.py"
container_python "${staging}/test_create_gdp_cem_e11_d3_manifest.py" >/dev/null
container_python "${staging}/test_analyze_gdp_cem_e11_d3.py" >/dev/null
printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  "upstream_source_manifest_sha256=${BASE_MANIFEST}" \
  'checks=python_compile,shell_syntax,velocity_sampler,velocity_cfg,latent_rollout,synthetic_manifest_selection,no_overwrite_publish,full_576_shard_synthetic_aggregate,array_bijection,seed_namespaces' \
  'd3_read=false' \
  'protected_c1_i1_read=false' \
  > "${staging}/E11-STATIC-PREFLIGHT-PASSED.txt"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e11-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
