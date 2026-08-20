#!/usr/bin/env bash
set -euo pipefail
: "${SNAPSHOT:?run with immutable v3 snapshot path}"
: "${TRAIN_JOB_ID:?run with residual training array ID}"
: "${MANIFEST_JOB_ID:?run with D2 manifest job ID}"
: "${STAGE_A_JOB_ID:?run with passing Stage-A analysis job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
AUTH=${ROOT}/results/acid-alternative/v3-d2/stage-a/analysis/job-${STAGE_A_JOB_ID}/stage-b-authorization.json
test -f "${AUTH}"
submit() {
  local result
  result=$(sbatch --parsable "$@")
  [[ "${result}" =~ ^[0-9]+$ ]] || { printf 'invalid sbatch response: %q\n' "${result}" >&2; exit 2; }
  printf '%s' "${result}"
}
stage_b=$(submit --export=ALL,SNAPSHOT="${SNAPSHOT}",TRAIN_JOB_ID="${TRAIN_JOB_ID}",MANIFEST_JOB_ID="${MANIFEST_JOB_ID}",STAGE_A_JOB_ID="${STAGE_A_JOB_ID}" "${SNAPSHOT}/run_acid_alt_v3_stage_b.slurm")
analysis=$(submit --dependency=afterok:"${stage_b}" --export=ALL,SNAPSHOT="${SNAPSHOT}",STAGE_A_JOB_ID="${STAGE_A_JOB_ID}",STAGE_B_JOB_ID="${stage_b}" "${SNAPSHOT}/run_acid_alt_v3_stage_b_analyze.slurm")
ledger=${ROOT}/results/acid-alternative/v3-d2/submissions/stage-b-${analysis}.tsv
mkdir -p "$(dirname "${ledger}")"
printf 'stage\tjob_id\nstage_b\t%s\nanalysis\t%s\n' "${stage_b}" "${analysis}" > "${ledger}"
sha256sum "${ledger}" > "${ledger}.sha256"
cat "${ledger}"
