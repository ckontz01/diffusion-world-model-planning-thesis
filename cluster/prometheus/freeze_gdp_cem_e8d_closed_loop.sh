#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e8d_closed_loop.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e8d_closed_loop.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
BASE=${ROOT}/snapshots/gdp-cem-e8a-refinement-d4003deb1f5b0681
BASE_MANIFEST=d4003deb1f5b068112dd3023ab96ce45c0e2f24efd53af8ca75c1b6e36bd5bea
PROTOCOL_SHA=da502adde1bb53794e6552a185799ea7a19fdd557f0a927f2b1b395830f6a5ba
test "${output_parent}" = "${ROOT}/snapshots"
test "$(sha256sum "${BASE}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = "${BASE_MANIFEST}"
(cd "${BASE}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)

staging=${output_parent}/.gdp-cem-e8d-closed-loop-staging-20260817
test ! -e "${staging}"
mkdir -p "${staging}"
cp -a "${BASE}/." "${staging}/"
chmod -R u+w "${staging}"
rm "${staging}/SOURCE-MANIFEST.sha256"
files=(
  ACID-ALTERNATIVE-E8D-GADR-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md
  ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md
  gdp_cem_models.py test_gdp_cem_models.py
  evaluate_gdp_cem_e8d_closed_loop.py analyze_gdp_cem_e8d_closed_loop.py
  test_analyze_gdp_cem_e8d_closed_loop.py preflight_gdp_cem_e8d.py
  run_gdp_cem_e8d_closed_loop.slurm
  run_gdp_cem_e8d_closed_loop_analyze.slurm
  submit_gdp_cem_e8d_closed_loop.sh freeze_gdp_cem_e8d_closed_loop.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E8D-GADR-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" | cut -d' ' -f1)" = c38e086ee09cbabaa9ab53246add92835d59f95173b5f35290f474abb94a4dfb
! grep -R --line-number --fixed-strings '__E8D_' "${staging}"
bash -n \
  "${staging}/run_gdp_cem_e8d_closed_loop.slurm" \
  "${staging}/run_gdp_cem_e8d_closed_loop_analyze.slurm" \
  "${staging}/submit_gdp_cem_e8d_closed_loop.sh" \
  "${staging}/freeze_gdp_cem_e8d_closed_loop.sh"

IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
container_python() {
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${staging}" \
    "${ENV_DIR}/bin/python" "$@"
}
container_python -m py_compile \
  "${staging}/gdp_cem_models.py" \
  "${staging}/evaluate_gdp_cem_e8d_closed_loop.py" \
  "${staging}/analyze_gdp_cem_e8d_closed_loop.py" \
  "${staging}/preflight_gdp_cem_e8d.py"
for test_script in \
  test_gdp_cem_models.py \
  test_gdp_cem_latent_rollout.py \
  test_analyze_gdp_cem_e8d_closed_loop.py
do
  container_python "${staging}/${test_script}"
done
container_python "${staging}/preflight_gdp_cem_e8d.py" \
  --root "${ROOT}" --source-manifest "${BASE}/SOURCE-MANIFEST.sha256"
printf '%s\n' \
  'status=passed' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  "upstream_source_manifest_sha256=${BASE_MANIFEST}" \
  'checks=python_compile,model_oracle_rng_solver_tests,latent_rollout_tests,analysis_gate_tests,lineage_preflight,protected_path_tests' \
  > "${staging}/E8D-PREFLIGHT-PASSED.txt"

find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e8d-closed-loop-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
