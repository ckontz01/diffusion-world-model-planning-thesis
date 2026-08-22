#!/usr/bin/env bash
set -euo pipefail
mode=${1:?usage: submit_gdp_cem_e13.sh pre-d4 SNAPSHOT | d4 SNAPSHOT PREFLIGHT_JOB SMOKE_JOB}
SNAPSHOT=${2:?usage: submit_gdp_cem_e13.sh pre-d4 SNAPSHOT | d4 SNAPSHOT PREFLIGHT_JOB SMOKE_JOB}
ROOT=/lustreFS/data/superworld/ckontzias/thesis
PROTOCOL_SHA=65d56b613f12ad896c395e6feb4fc6d39f404bc802045369d0a88b638690af58
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sed -n 's/^status=//p' "${SNAPSHOT}/E13-STATIC-PREFLIGHT-PASSED.txt")" = passed
test "$(sed -n 's/^protocol_sha256=//p' "${SNAPSHOT}/E13-STATIC-PREFLIGHT-PASSED.txt")" = "${PROTOCOL_SHA}"

case "${mode}" in
  pre-d4)
    test "$#" -eq 2
    test ! -e "${ROOT}/manifests/gdp-cem-e13-d4"
    test ! -e "${ROOT}/results/acid-alternative/gdp-cem-e13-d4"
    preflight=$(sbatch --parsable --export=ALL,SNAPSHOT="${SNAPSHOT}" "${SNAPSHOT}/run_gdp_cem_e13_preflight.slurm")
    preflight=${preflight%%;*}
    [[ "${preflight}" =~ ^[0-9]+$ ]] || exit 2
    smoke=$(sbatch --parsable --dependency="afterok:${preflight}" \
      --export=ALL,SNAPSHOT="${SNAPSHOT}",PREFLIGHT_JOB_ID="${preflight}" \
      "${SNAPSHOT}/run_gdp_cem_e13_p1_smoke.slurm")
    smoke=${smoke%%;*}
    [[ "${smoke}" =~ ^[0-9]+$ ]] || exit 2
    printf 'phase=pre-d4\nsnapshot=%s\npreflight_job=%s\np1_smoke_array_job=%s\n' \
      "${SNAPSHOT}" "${preflight}" "${smoke}"
    ;;
  d4)
    test "$#" -eq 4
    PREFLIGHT_JOB_ID=$3
    SMOKE_JOB_ID=$4
    [[ "${PREFLIGHT_JOB_ID}" =~ ^[0-9]+$ && "${SMOKE_JOB_ID}" =~ ^[0-9]+$ ]] || exit 2
    PREFLIGHT=${ROOT}/results/acid-alternative/gdp-cem-e13/preflight/job-${PREFLIGHT_JOB_ID}
    test -f "${PREFLIGHT}/sha256.txt"
    (cd "${PREFLIGHT}" && sha256sum -c sha256.txt >/dev/null)
    for task_index in 0 1 2; do
      case "${task_index}" in 0) task=pusht ;; 1) task=reacher ;; 2) task=cube ;; esac
      arms=(latent_gaussian_select_k300 vp_select_k300 prism_dp_select_k300 vp_select_k16 prism_dp_select_k16)
      for arm_index in 0 1 2 3 4; do
        index=$((task_index * 5 + arm_index))
        directory=${ROOT}/results/acid-alternative/gdp-cem-e13/p1-smoke/${task}/${arms[${arm_index}]}/job-${SMOKE_JOB_ID}-${index}
        test -f "${directory}/sha256.txt"
        (cd "${directory}" && sha256sum -c sha256.txt >/dev/null)
      done
    done
    test ! -e "${ROOT}/manifests/gdp-cem-e13-d4"
    test ! -e "${ROOT}/results/acid-alternative/gdp-cem-e13-d4"
    manifest=$(sbatch --parsable \
      --export=ALL,SNAPSHOT="${SNAPSHOT}",PREFLIGHT_JOB_ID="${PREFLIGHT_JOB_ID}",SMOKE_JOB_ID="${SMOKE_JOB_ID}" \
      "${SNAPSHOT}/run_gdp_cem_e13_create_d4.slurm")
    manifest=${manifest%%;*}
    [[ "${manifest}" =~ ^[0-9]+$ ]] || exit 2
    evaluation=$(sbatch --parsable --dependency="afterok:${manifest}" \
      --export=ALL,SNAPSHOT="${SNAPSHOT}",MANIFEST_JOB_ID="${manifest}" \
      "${SNAPSHOT}/run_gdp_cem_e13_evaluate.slurm")
    evaluation=${evaluation%%;*}
    [[ "${evaluation}" =~ ^[0-9]+$ ]] || exit 2
    analysis=$(sbatch --parsable --dependency="afterok:${evaluation}" \
      --export=ALL,SNAPSHOT="${SNAPSHOT}",MANIFEST_JOB_ID="${manifest}",EVALUATION_JOB_ID="${evaluation}" \
      "${SNAPSHOT}/run_gdp_cem_e13_analyze.slurm")
    analysis=${analysis%%;*}
    [[ "${analysis}" =~ ^[0-9]+$ ]] || exit 2
    printf 'phase=d4\nsnapshot=%s\nmanifest_array_job=%s\nevaluation_array_job=%s\nanalysis_job=%s\n' \
      "${SNAPSHOT}" "${manifest}" "${evaluation}" "${analysis}"
    ;;
  *)
    echo "invalid E13 submission phase: ${mode}" >&2
    exit 2
    ;;
esac
