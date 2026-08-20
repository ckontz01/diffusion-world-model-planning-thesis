#!/usr/bin/env bash
set -euo pipefail
: "${SNAPSHOT:?run with immutable E3 snapshot path}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
TRAIN_JOB_ID=297533
MANIFEST_JOB_ID=297535

test -d "${SNAPSHOT}"
test "$(sha256sum "${SNAPSHOT}/ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-PROTOCOL-2026-08-16.md" | cut -d' ' -f1)" = c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0
(
  cd "${SNAPSHOT}"
  sha256sum -c SOURCE-MANIFEST.sha256
)

submit() {
  local result
  result=$(sbatch --parsable "$@")
  [[ "${result}" =~ ^[0-9]+$ ]] || {
    printf 'invalid sbatch response: %q\n' "${result}" >&2
    exit 2
  }
  printf '%s' "${result}"
}

authorization=$(submit \
  --export=ALL,SNAPSHOT="${SNAPSHOT}" \
  "${SNAPSHOT}/run_acid_alt_e3_authorize.slurm")
closed_loop=$(submit \
  --dependency=afterok:"${authorization}" \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",TRAIN_JOB_ID="${TRAIN_JOB_ID}",MANIFEST_JOB_ID="${MANIFEST_JOB_ID}",AUTH_JOB_ID="${authorization}" \
  "${SNAPSHOT}/run_acid_alt_e3_d2_closed_loop.slurm")
analysis=$(submit \
  --dependency=afterok:"${closed_loop}" \
  --export=ALL,SNAPSHOT="${SNAPSHOT}",AUTH_JOB_ID="${authorization}",E3_ARRAY_JOB_ID="${closed_loop}" \
  "${SNAPSHOT}/run_acid_alt_e3_d2_analyze.slurm")

ledger=${ROOT}/results/acid-alternative/e3-d2-exploratory/submissions/analysis-${analysis}.tsv
mkdir -p "$(dirname "${ledger}")"
printf 'stage\tjob_id\nexploratory_authorization\t%s\nclosed_loop_array_54_runs\t%s\nexploratory_analysis\t%s\n' \
  "${authorization}" "${closed_loop}" "${analysis}" > "${ledger}"
printf 'protocol_sha256\t%s\nsource_manifest_sha256\t%s\nv3_stage_a_summary_sha256\t%s\nv3_stage_b_authorized\tfalse\nconfirmation_claim_allowed\tfalse\nprotected_c1_i1_read\tfalse\n' \
  c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0 \
  "$(sha256sum "${SNAPSHOT}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" \
  0af2181b1060d761a295c885f2eae34af47a0fd94992a8f3a59cf05e57ecbe37 >> "${ledger}"
sha256sum "${ledger}" > "${ledger}.sha256"
cat "${ledger}"
