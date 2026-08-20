#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e12_stage_b.sh IMMUTABLE_SNAPSHOT}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sed -n 's/^status=//p' "${SNAPSHOT}/E12-STAGE-B-STATIC-PREFLIGHT-PASSED.txt")" = passed
test "$(sed -n 's/^protocol_sha256=//p' "${SNAPSHOT}/E12-STAGE-B-STATIC-PREFLIGHT-PASSED.txt")" = 08cbe26c3186f06d6731defc8fc66f63c2a55c1102f6d089f1e286176f9ed927
ROOT=/lustreFS/data/superworld/ckontzias/thesis
test ! -e "${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b"
preflight=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e12_stage_b_preflight.slurm")
preflight=${preflight%%;*}
[[ "${preflight}" =~ ^[0-9]+$ ]] || exit 2
smoke=$(sbatch --parsable --dependency="afterok:${preflight}" --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e12_stage_b_gpu_smoke.slurm")
smoke=${smoke%%;*}
[[ "${smoke}" =~ ^[0-9]+$ ]] || exit 2
heads=$(sbatch --parsable --dependency="afterok:${smoke}" --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e12_prism_head_train.slurm")
heads=${heads%%;*}
[[ "${heads}" =~ ^[0-9]+$ ]] || exit 2
dp=$(sbatch --parsable --dependency="afterok:${smoke}" --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e12_prism_dp_train.slurm")
dp=${dp%%;*}
[[ "${dp}" =~ ^[0-9]+$ ]] || exit 2
printf 'snapshot=%s\npreflight_job=%s\ngpu_smoke_job=%s\nprism_head_array_job=%s\nprism_dp_array_job=%s\n' \
  "${SNAPSHOT}" "${preflight}" "${smoke}" "${heads}" "${dp}"
