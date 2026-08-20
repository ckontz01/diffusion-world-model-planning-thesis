#!/usr/bin/env bash

# Build read-only, content-addressed core, diagnostic, and orchestration snapshots.

set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "usage: $0 STAGED_PROMETHEUS_DIR SNAPSHOT_PARENT" >&2
  exit 2
fi
SOURCE="$(cd "$1" && pwd -P)"
SNAPSHOT_PARENT="$2"
mkdir -p "${SNAPSHOT_PARENT}"
SNAPSHOT_PARENT="$(cd "${SNAPSHOT_PARENT}" && pwd -P)"
if [[ "${SOURCE}" == "${SNAPSHOT_PARENT}" || "${SNAPSHOT_PARENT}" == "${SOURCE}/"* ]]; then
  echo "snapshot parent must not be the staged source tree" >&2
  exit 2
fi
WORK="$(mktemp -d "${SNAPSHOT_PARENT}/.acid-alt-freeze.XXXXXX")"
case "${WORK}" in
  "${SNAPSHOT_PARENT}/.acid-alt-freeze."*) ;;
  *) echo "unsafe temporary freeze path: ${WORK}" >&2; exit 2 ;;
esac
trap 'rm -rf -- "${WORK}"' EXIT

copy_python_tree() {
  local package="$1" destination="$2" file relative
  while IFS= read -r -d '' file; do
    relative="${file#"${SOURCE}/"}"
    mkdir -p "${destination}/$(dirname "${relative}")"
    cp -p -- "${file}" "${destination}/${relative}"
  done < <(find "${SOURCE}/${package}" -type f -name '*.py' -print0 | sort -z)
}

mkdir -p "${WORK}/core" "${WORK}/diagnostics" "${WORK}/orchestration/tests" \
  "${WORK}/orchestration/docs"
copy_python_tree acid_alternative "${WORK}/core"
copy_python_tree acid_alternative_diagnostics "${WORK}/diagnostics"

orchestration_files=(
  authorize_acid_alt_lewm_c1.sh
  freeze_acid_alt_sources.sh
  submit_acid_alt_lewm_d1.sh
  submit_acid_alt_lewm_c1.sh
  run_prepare_acid_alt_task.slurm
  run_acid_alt_diagnostic_preflight.slurm
  run_acid_alt_task_preflight.slurm
  run_acid_alt_task_p1_latents.slurm
  run_acid_alt_task_transition_cache.slurm
  run_acid_alt_task_reachability_pairs.slurm
  run_acid_alt_task_core_scorers.slurm
  run_acid_alt_task_transition_controls.slurm
  run_acid_alt_task_reachability_heads.slurm
  run_acid_alt_task_b0_r0.slurm
  run_acid_alt_task_a1_r0.slurm
  run_acid_alt_task_r0_gate.slurm
  run_acid_alt_task_d1_primary.slurm
  run_acid_alt_task_capture_candidates.slurm
  run_acid_alt_task_score_candidates.slurm
  run_acid_alt_task_execute_candidates.slurm
  run_acid_alt_task_analyze_candidates.slurm
  run_acid_alt_task_sensitivity.slurm
  run_acid_alt_task_latency_cuda.slurm
  run_acid_alt_task_latency_episode.slurm
  run_acid_alt_analyze_closed_loop.slurm
  run_acid_alt_analyze_validation_all_tasks.slurm
  run_acid_alt_aggregate_mechanism.slurm
  run_acid_alt_analyze_sensitivity.slurm
  run_acid_alt_task_c1_primary.slurm
  run_acid_alt_task_i1_latents.slurm
  run_acid_alt_task_i1_transition_cache.slurm
  run_acid_alt_task_c1_identification.slurm
  run_acid_alt_assemble_c1_claim.slurm
)
for file in "${orchestration_files[@]}"; do
  test -f "${SOURCE}/${file}"
  cp -p -- "${SOURCE}/${file}" "${WORK}/orchestration/${file}"
done
cp -p -- "${SOURCE}/tests/test_submission_graphs.sh" \
  "${WORK}/orchestration/tests/test_submission_graphs.sh"
for file in ACID-ALTERNATIVE-V1-PROTOCOL-2026-08-12.md \
  ACID-ALTERNATIVE-V1-AMENDMENTS-2026-08-13.md \
  ACID-ALTERNATIVE-V1-RUNBOOK-2026-08-14.md; do
  test -f "${SOURCE}/${file}"
  cp -p -- "${SOURCE}/${file}" "${WORK}/orchestration/docs/${file}"
done

publish_snapshot() {
  local component="$1" prefix="$2" manifest tree_hash short final
  manifest="${WORK}/${component}/SOURCE-MANIFEST.sha256"
  (
    cd "${WORK}/${component}"
    find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
      | sort -z | xargs -0 sha256sum > SOURCE-MANIFEST.sha256
    sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null
  )
  tree_hash="$(sha256sum "${manifest}" | awk '{print $1}')"
  short="${tree_hash:0:16}"
  final="${SNAPSHOT_PARENT}/${prefix}-${short}"
  if [[ -e "${final}" ]]; then
    echo "refusing existing snapshot: ${final}" >&2
    exit 2
  fi
  mv -- "${WORK}/${component}" "${final}"
  chmod -R a-w "${final}"
  printf '%s_snapshot=%s\n%s_tree_sha256=%s\n' \
    "${component}" "${final}" "${component}" "${tree_hash}"
}

publish_snapshot core acid-alternative-core-v1
publish_snapshot diagnostics acid-alternative-diagnostics-v1
publish_snapshot orchestration acid-alternative-orchestration-v1
