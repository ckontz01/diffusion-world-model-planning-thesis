#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e10v.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e10v.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e8a-refinement-d4003deb1f5b0681
BASE_MANIFEST=d4003deb1f5b068112dd3023ab96ce45c0e2f24efd53af8ca75c1b6e36bd5bea
PROTOCOL_SHA=2f3052637e72016d4218fd6e13c62d36589773f23a9a0b4223c9a808e9fab93a
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)

staging=${output_parent}/.gdp-cem-e10v-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E10V-PURE-VELOCITY-DIFFUSION-P1-PROTOCOL-2026-08-17.md
  gdp_cem_models.py test_gdp_cem_models.py
  train_gdp_cem_vp_proposal.py evaluate_gdp_cem_e10v_p1.py
  analyze_gdp_cem_e10v_p1.py test_analyze_gdp_cem_e10v_p1.py
  preflight_gdp_cem_e10v.py
  run_gdp_cem_e10v_train.slurm run_gdp_cem_e10v_evaluate.slurm
  run_gdp_cem_e10v_analyze.slurm submit_gdp_cem_e10v.sh
  freeze_gdp_cem_e10v.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E10V-PURE-VELOCITY-DIFFUSION-P1-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
if grep -R --line-number --fixed-strings \
  --exclude=freeze_gdp_cem_e10v.sh '__E10V_' "${staging}"
then
  echo "unresolved E10V placeholder" >&2
  exit 2
fi
bash -n \
  "${staging}/run_gdp_cem_e10v_train.slurm" \
  "${staging}/run_gdp_cem_e10v_evaluate.slurm" \
  "${staging}/run_gdp_cem_e10v_analyze.slurm" \
  "${staging}/submit_gdp_cem_e10v.sh" \
  "${staging}/freeze_gdp_cem_e10v.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
container_python() {
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
    "${ENV_DIR}/bin/python" "$@"
}
container_python -m py_compile \
  "${staging}/gdp_cem_models.py" \
  "${staging}/train_gdp_cem_vp_proposal.py" \
  "${staging}/evaluate_gdp_cem_e10v_p1.py" \
  "${staging}/analyze_gdp_cem_e10v_p1.py" \
  "${staging}/preflight_gdp_cem_e10v.py"
for test_script in \
  test_gdp_cem_models.py \
  test_gdp_cem_latent_rollout.py \
  test_analyze_gdp_cem_e10v_p1.py
do
  container_python "${staging}/${test_script}"
done
container_python "${staging}/preflight_gdp_cem_e10v.py" \
  --root "${ROOT}" \
  --source-manifest "${BASE}/SOURCE-MANIFEST.sha256" \
  --protocol "${staging}/ACID-ALTERNATIVE-E10V-PURE-VELOCITY-DIFFUSION-P1-PROTOCOL-2026-08-17.md"
printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  "upstream_source_manifest_sha256=${BASE_MANIFEST}" \
  'checks=python_compile,velocity_oracle_cfg_determinism,model_overfit,latent_rollout,row_isolation,gate_tests,control_lineage,protected_path_tests' \
  > "${staging}/E10V-PREFLIGHT-PASSED.txt"

find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e10v-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
