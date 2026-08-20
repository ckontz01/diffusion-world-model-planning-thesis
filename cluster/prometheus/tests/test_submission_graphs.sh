#!/usr/bin/env bash

# Functional dry run of both orchestration graphs with a deterministic sbatch stub.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "${TMP}"' EXIT
ROOT="${TMP}/root"; CORE="${TMP}/core"; DIAG="${TMP}/diag"; ORCH="${TMP}/orch"
mkdir -p "${ROOT}" "${CORE}" "${DIAG}" "${ORCH}" "${TMP}/bin"
for snapshot in "${CORE}" "${DIAG}" "${ORCH}"; do
  printf 'snapshot fixture\n' > "${snapshot}/fixture.txt"
  (cd "${snapshot}" && sha256sum fixture.txt > SOURCE-MANIFEST.sha256)
done
cat > "${TMP}/bin/sbatch" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
counter_file="${MOCK_SBATCH_COUNTER:?}"
script="${!#}"
case "$(basename "${script}")" in
  run_acid_alt_task_capture_candidates.slurm|\
  run_acid_alt_task_score_candidates.slurm|\
  run_acid_alt_task_execute_candidates.slurm|\
  run_acid_alt_task_sensitivity.slurm|\
  run_acid_alt_task_c1_primary.slurm|\
  run_acid_alt_task_i1_latents.slurm|\
  run_acid_alt_task_i1_transition_cache.slurm|\
  run_acid_alt_task_c1_identification.slurm)
    found=false
    for argument in "$@"; do
      if [[ "${argument}" == --export=* && "${argument}" == *"ORCH_SNAPSHOT=${MOCK_ORCH_SNAPSHOT:?}"* ]]; then
        found=true
      fi
    done
    if [[ "${found}" != true ]]; then
      echo "missing explicit immutable ORCH_SNAPSHOT export for ${script}" >&2
      exit 90
    fi
    ;;
esac
value=300000
if [[ -f "${counter_file}" ]]; then value="$(<"${counter_file}")"; fi
value=$((value + 1))
printf '%s\n' "${value}" > "${counter_file}"
printf '%s\n' "${value}"
SH
chmod +x "${TMP}/bin/sbatch"
export PATH="${TMP}/bin:${PATH}" MOCK_SBATCH_COUNTER="${TMP}/counter" \
  MOCK_ORCH_SNAPSHOT="${ORCH}" THESIS_ROOT="${ROOT}"

d1_output="$(bash "${SCRIPT_DIR}/submit_acid_alt_lewm_d1.sh" "${CORE}" "${DIAG}" "${ORCH}")"
d1_state="$(printf '%s\n' "${d1_output}" | sed -n 's/^submission_state=//p' | head -n 1)"
test -f "${d1_state}"; test -f "${d1_state}.sha256"
grep -q $'^all\tclosed_loop_development\t' "${d1_state}"
grep -q $'^all\tmechanism\t' "${d1_state}"
grep -q $'^cube\tsensitivity\t' "${d1_state}"

fixture="${TMP}/complete-d1.tsv"
printf 'task\tstage\tjob_id\n' > "${fixture}"
job=410000
for task in pusht reacher cube; do
  for stage in core controls reachability latent transition preflight; do
    job=$((job + 1)); printf '%s\t%s\t%s\n' "${task}" "${stage}" "${job}" >> "${fixture}"
  done
done
sha256sum "${fixture}" > "${fixture}.sha256"
authorization="${TMP}/c1-authorization.json"
printf '{}\n' > "${authorization}"
sha256sum "${authorization}" > "${authorization}.sha256"
c1_output="$(bash "${SCRIPT_DIR}/submit_acid_alt_lewm_c1.sh" "${CORE}" "${DIAG}" "${ORCH}" "${authorization}" "${fixture}")"
c1_state="$(printf '%s\n' "${c1_output}" | sed -n 's/^submission_state=//p' | head -n 1)"
test -f "${c1_state}"; test -f "${c1_state}.sha256"
grep -q $'^all\tclosed_loop_confirmation\t' "${c1_state}"
grep -q $'^all\tclaim_decision\t' "${c1_state}"
grep -q $'^all\tsensitivity_analysis\t' "${c1_state}"
grep -q $'^pusht\ti1_latent\t' "${c1_state}"
grep -q $'^pusht\ti1_transition\t' "${c1_state}"
grep -q $'^pusht\tidentification\t' "${c1_state}"
printf 'submission graph dry run: OK\n'
