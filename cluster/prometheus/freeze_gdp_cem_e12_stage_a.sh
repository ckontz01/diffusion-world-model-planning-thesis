#!/usr/bin/env bash
set -euo pipefail
source_root=${1:?usage: freeze_gdp_cem_e12_stage_a.sh STAGED_SOURCE OUTPUT_PARENT}
output_parent=${2:?usage: freeze_gdp_cem_e12_stage_a.sh STAGED_SOURCE OUTPUT_PARENT}
source_root=$(cd "${source_root}" && pwd -P)
output_parent=$(cd "${output_parent}" && pwd -P)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
PROTOCOL_SHA=08cbe26c3186f06d6731defc8fc66f63c2a55c1102f6d089f1e286176f9ed927
test "${output_parent}" = "${ROOT}/snapshots"
staging=${output_parent}/.gdp-cem-e12-stage-a-staging-20260820
test ! -e "${staging}"
mkdir -p "${staging}"
files=(
  ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md
  gdp_cem_e11_specs.py gdp_cem_e12_specs.py
  gdp_cem_e12_prism_models.py gdp_cem_e12_prism_data.py
  preflight_gdp_cem_e12_stage_b.py evaluate_gdp_cem_e12_stage_a_native.py
  run_gdp_cem_e12_stage_a_native.slurm submit_gdp_cem_e12_stage_a.sh
  freeze_gdp_cem_e12_stage_a.sh
)
for file in "${files[@]}"; do
  test -f "${source_root}/${file}"
  cp "${source_root}/${file}" "${staging}/${file}"
done
test "$(sha256sum "${staging}/ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md" | cut -d' ' -f1)" = "${PROTOCOL_SHA}"
bash -n "${staging}/run_gdp_cem_e12_stage_a_native.slurm" "${staging}/submit_gdp_cem_e12_stage_a.sh" "${staging}/freeze_gdp_cem_e12_stage_a.sh"
grep -Fq 'video_path=scratch_video_path' "${staging}/evaluate_gdp_cem_e12_stage_a_native.py"
! grep -Fq 'video_path=None' "${staging}/evaluate_gdp_cem_e12_stage_a_native.py"
grep -Fq 'PYOPENGL_PLATFORM=egl' "${staging}/run_gdp_cem_e12_stage_a_native.slurm"
grep -Fq '/usr/share/glvnd/egl_vendor.d/10_nvidia.json' "${staging}/run_gdp_cem_e12_stage_a_native.slurm"
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
PRISM=${ROOT}/downloads/prism-jepa-baa0eb95
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${staging}:${PRISM}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m py_compile "${staging}/evaluate_gdp_cem_e12_stage_a_native.py"
test "$(git -C "${PRISM}" rev-parse HEAD)" = baa0eb95efb812196b68796c258b1f0cf10b7625
sha256sum -c <<'EOF'
82d37a9d9338d8c23005017ab5c1ff91c8b5e3fd51fafbd620af8457c381d125  /lustreFS/data/superworld/ckontzias/thesis/downloads/prism-hf-cube-6da8f34ef31bf25b/lewm_object.ckpt
0bbfacb047d7ea68370d07a56185099807cc1a9536034fbe53cdbfb3f6d78dec  /lustreFS/data/superworld/ckontzias/thesis/downloads/prism-hf-cube-6da8f34ef31bf25b/prior_head_cube.pt
04ef1349322494ef1614cbd422577d28cd239516da264b14edc645235ea4b2ac  /lustreFS/data/superworld/ckontzias/thesis/downloads/prism-hf-cube-6da8f34ef31bf25b/README.md
4f4a3c9cd30c4bb265c991cb7a4607f90bebddcb47b59e8020cf4b9279a1f0b3  /lustreFS/data/superworld/ckontzias/thesis/downloads/prism-hf-pusht-40461a2269da322c/lewm_object.ckpt
e4dae35d16ada9768e7371e368508c3927ba1487fe10bd5402ff7869f1972191  /lustreFS/data/superworld/ckontzias/thesis/downloads/prism-hf-pusht-40461a2269da322c/prior_head_pusht.pt
378e44561fcf9176b9a222a54d73b3c913012ac0e817adee5eeb2e68f8816f32  /lustreFS/data/superworld/ckontzias/thesis/downloads/prism-hf-pusht-40461a2269da322c/README.md
EOF
printf '%s\n' \
  'status=passed' \
  'prism_git_commit=baa0eb95efb812196b68796c258b1f0cf10b7625' \
  'cube_huggingface_revision=6da8f34ef31bf25b6eb78cd7669c862b11360046' \
  'pusht_huggingface_revision=40461a2269da322c24738835880a3aef768828e8' \
  "protocol_sha256=${PROTOCOL_SHA}" \
  > "${staging}/E12-STAGE-A-ARTIFACT-PREFLIGHT-PASSED.txt"
find "${staging}" -type d -name __pycache__ -prune -exec rm -r -- {} +
(cd "${staging}" && find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
  | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256 \
  && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
manifest_hash=$(sha256sum "${staging}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
destination=${output_parent}/gdp-cem-e12-stage-a-${manifest_hash:0:16}
test ! -e "${destination}"
mv "${staging}" "${destination}"
chmod -R a-w "${destination}"
printf 'snapshot=%s\nsource_manifest_sha256=%s\n' "${destination}" "${manifest_hash}"
