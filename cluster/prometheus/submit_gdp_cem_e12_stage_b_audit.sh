#!/usr/bin/env bash
set -euo pipefail
SNAPSHOT=${1:?usage: submit_gdp_cem_e12_stage_b_audit.sh AUDIT_SNAPSHOT TRAINING_SNAPSHOT HEAD_JOB DP_JOB}
TRAINING_SNAPSHOT=${2:?usage: submit_gdp_cem_e12_stage_b_audit.sh AUDIT_SNAPSHOT TRAINING_SNAPSHOT HEAD_JOB DP_JOB}
HEAD_JOB=${3:?usage: submit_gdp_cem_e12_stage_b_audit.sh AUDIT_SNAPSHOT TRAINING_SNAPSHOT HEAD_JOB DP_JOB}
DP_JOB=${4:?usage: submit_gdp_cem_e12_stage_b_audit.sh AUDIT_SNAPSHOT TRAINING_SNAPSHOT HEAD_JOB DP_JOB}
ROOT=/lustreFS/data/superworld/ckontzias/thesis
[[ "${HEAD_JOB}" =~ ^[0-9]+$ && "${DP_JOB}" =~ ^[0-9]+$ ]] || exit 2
test -d "${SNAPSHOT}" && test ! -w "${SNAPSHOT}"
test -d "${TRAINING_SNAPSHOT}" && test ! -w "${TRAINING_SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${TRAINING_SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${ROOT}/results/acid-alternative/gdp-cem-e12/stage-b/STAGE-B-AUDIT.json"
job=$(sbatch --parsable --dependency="afterany:${HEAD_JOB}:${DP_JOB}" \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",TRAINING_SNAPSHOT="${TRAINING_SNAPSHOT}" \
  "${SNAPSHOT}/run_gdp_cem_e12_stage_b_audit.slurm")
job=${job%%;*}
[[ "${job}" =~ ^[0-9]+$ ]] || exit 2
printf 'audit_snapshot=%s\ntraining_snapshot=%s\nstage_b_audit_job=%s\n' \
  "${SNAPSHOT}" "${TRAINING_SNAPSHOT}" "${job}"
