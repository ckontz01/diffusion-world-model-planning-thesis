#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e10m.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e10m.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e10v-b843a68dda335549
BASE_MANIFEST=b843a68dda3355499cada1d580853654efa404bc5f5d2375fbee14b4121e3e5d
PROTOCOL_SHA=02606573e4c7e4341814c76974ff2020f35fedcf2e8d1d08e531dd553e9787b9
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
staging=${output_parent}/.gdp-cem-e10m-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E10M-MULTISEED-PURE-VELOCITY-P1-PROTOCOL-2026-08-17.md
  train_gdp_cem_e10m_models.py evaluate_gdp_cem_e10m_p1.py
  analyze_gdp_cem_e10m_p1.py test_analyze_gdp_cem_e10m_p1.py
  preflight_gdp_cem_e10m.py
  run_gdp_cem_e10m_train.slurm run_gdp_cem_e10m_evaluate.slurm
  run_gdp_cem_e10m_analyze.slurm submit_gdp_cem_e10m.sh
  freeze_gdp_cem_e10m.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E10M-MULTISEED-PURE-VELOCITY-P1-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
if grep -R --line-number --fixed-strings \
  --exclude=freeze_gdp_cem_e10m.sh '__E10M_' "${staging}"
then
  echo "unresolved E10M placeholder" >&2
  exit 2
fi
bash -n \
  "${staging}/run_gdp_cem_e10m_train.slurm" \
  "${staging}/run_gdp_cem_e10m_evaluate.slurm" \
  "${staging}/run_gdp_cem_e10m_analyze.slurm" \
  "${staging}/submit_gdp_cem_e10m.sh" \
  "${staging}/freeze_gdp_cem_e10m.sh"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
container_python() {
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
    "${ENV_DIR}/bin/python" "$@"
}
container_python -m py_compile \
  "${staging}/train_gdp_cem_e10m_models.py" \
  "${staging}/evaluate_gdp_cem_e10m_p1.py" \
  "${staging}/analyze_gdp_cem_e10m_p1.py" \
  "${staging}/preflight_gdp_cem_e10m.py"
for test_script in \
  test_gdp_cem_models.py \
  test_gdp_cem_latent_rollout.py \
  test_analyze_gdp_cem_e10m_p1.py
do
  container_python "${staging}/${test_script}"
done
container_python "${staging}/preflight_gdp_cem_e10m.py" \
  --root "${ROOT}" \
  --source-manifest "${BASE}/SOURCE-MANIFEST.sha256" \
  --protocol "${staging}/ACID-ALTERNATIVE-E10M-MULTISEED-PURE-VELOCITY-P1-PROTOCOL-2026-08-17.md"
printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  "upstream_source_manifest_sha256=${BASE_MANIFEST}" \
  'checks=python_compile,velocity_cfg_tests,latent_rollout,confirmation_row_isolation,multiseed_gate_tests,seed1_model_lineage,protected_path_tests' \
  > "${staging}/E10M-PREFLIGHT-PASSED.txt"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e10m-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
