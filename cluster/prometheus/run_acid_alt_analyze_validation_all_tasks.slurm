#!/usr/bin/env bash

# Three-task held-out correct-action identification, including the shuffled null.

#SBATCH --job-name=acid-alt-validation
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-validation-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-validation-%j.err

set -euo pipefail
: "${ANALYSIS_ROLE:?submit with ANALYSIS_ROLE=D1|C1}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
[[ "${ANALYSIS_ROLE}" == D1 || "${ANALYSIS_ROLE}" == C1 ]] || { echo "invalid ANALYSIS_ROLE" >&2; exit 2; }
if [[ "${ANALYSIS_ROLE}" == D1 ]]; then
  for task in PUSHT REACHER CUBE; do eval ": \"\${${task}_CORE_SCORER_JOB_ID:?missing ${task}_CORE_SCORER_JOB_ID}\""; eval ": \"\${${task}_CONTROL_JOB_ID:?missing ${task}_CONTROL_JOB_ID}\""; done
else
  for task in PUSHT REACHER CUBE; do eval ": \"\${${task}_IDENTIFICATION_JOB_ID:?missing ${task}_IDENTIFICATION_JOB_ID}\""; done
fi
OUTPUT="${ROOT}/results/acid-alternative/analysis/${ANALYSIS_ROLE,,}/validation-identification/job-${SLURM_JOB_ID}"
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output: ${OUTPUT}" >&2; exit 2; fi
runs=(); seeds=(6101 6102 6103)
for task in pusht reacher cube; do
  prefix="${task^^}"
  if [[ "${ANALYSIS_ROLE}" == D1 ]]; then eval "core_job=\${${prefix}_CORE_SCORER_JOB_ID}"; eval "control_job=\${${prefix}_CONTROL_JOB_ID}"; else eval "identification_job=\${${prefix}_IDENTIFICATION_JOB_ID}"; fi
  for index in 0 1 2; do
    seed="${seeds[${index}]}"
    if [[ "${ANALYSIS_ROLE}" == D1 ]]; then
      runs+=(--run "${task}=${ROOT}/results/acid-alternative/scorers/${task}/diffusion/true/seed-${seed}-job-${core_job}-$((3 + index))/summary.json")
      runs+=(--run "${task}=${ROOT}/results/acid-alternative/scorers/${task}/forward/true/seed-${seed}-job-${core_job}-$((6 + index))/summary.json")
      runs+=(--run "${task}=${ROOT}/results/acid-alternative/scorers/${task}/diffusion/shuffled_action/seed-${seed}-job-${control_job}-${index}/summary.json")
    else
      runs+=(--run "${task}=${ROOT}/results/acid-alternative/identification/c1/${task}/diffusion/true/seed-${seed}-job-${identification_job}-${index}/summary.json")
      runs+=(--run "${task}=${ROOT}/results/acid-alternative/identification/c1/${task}/forward/true/seed-${seed}-job-${identification_job}-$((3 + index))/summary.json")
      runs+=(--run "${task}=${ROOT}/results/acid-alternative/identification/c1/${task}/diffusion/shuffled_action/seed-${seed}-job-${identification_job}-$((6 + index))/summary.json")
    fi
  done
done
for ((index=1; index<${#runs[@]}; index+=2)); do declaration="${runs[${index}]}"; test -f "${declaration#*=}"; done
mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" \
  -m acid_alternative_diagnostics.analyze_validation_identification \
  --analysis-role "${ANALYSIS_ROLE}" --source-manifest "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --bootstrap-repetitions 100000 --output-dir "${OUTPUT}" "${runs[@]}"
printf '%s\n' "analysis_role=${ANALYSIS_ROLE}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  "${OUTPUT}/summary.json" "${OUTPUT}/episode-identification.tsv" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
