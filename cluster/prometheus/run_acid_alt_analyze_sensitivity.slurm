#!/usr/bin/env bash

# Validate and summarize all three 105-run D1 or C1 sensitivity arrays.

#SBATCH --job-name=acid-alt-sensitivity-all
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-sensitivity-all-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-sensitivity-all-%j.err

set -euo pipefail
: "${ANALYSIS_ROLE:?submit with ANALYSIS_ROLE=D1|C1}"; : "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"; : "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"; : "${PUSHT_SENSITIVITY_JOB_ID:?submit with PushT sensitivity array ID}"; : "${REACHER_SENSITIVITY_JOB_ID:?submit with Reacher sensitivity array ID}"; : "${CUBE_SENSITIVITY_JOB_ID:?submit with Cube sensitivity array ID}"
[[ "${ANALYSIS_ROLE}" == D1 || "${ANALYSIS_ROLE}" == C1 ]] || { echo "invalid ANALYSIS_ROLE" >&2; exit 2; }
namespace="${ANALYSIS_ROLE,,}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; OUTPUT="${ROOT}/results/acid-alternative/analysis/${namespace}/sensitivity/job-${SLURM_JOB_ID}"
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi
tasks=(pusht reacher cube); jobs=("${PUSHT_SENSITIVITY_JOB_ID}" "${REACHER_SENSITIVITY_JOB_ID}" "${CUBE_SENSITIVITY_JOB_ID}"); arms=(b0 acid reachability diffusion forward); seeds=(6101 6102 6103); settings=(); setting_arms=(); setting_seeds=()
for label in pop30-lambda007 pop50-lambda007 pop150-lambda007 pop300-lambda007; do for arm in "${arms[@]}"; do for seed_index in 0 1 2; do settings+=("${label}"); setting_arms+=("${arm}"); setting_seeds+=("${seed_index}"); done; done; done
for label in pop300-lambda0005 pop300-lambda004 pop300-lambda010; do for arm in acid reachability diffusion forward; do for seed_index in 0 1 2; do settings+=("${label}"); setting_arms+=("${arm}"); setting_seeds+=("${seed_index}"); done; done; done
for label in pop300-lambda007-sigma010 pop300-lambda007-sigma025 pop300-lambda007-sigma050; do for seed_index in 0 1 2; do settings+=("${label}"); setting_arms+=(diffusion); setting_seeds+=("${seed_index}"); done; done
[[ ${#settings[@]} -eq 105 ]] || { echo "internal sensitivity analysis matrix error" >&2; exit 2; }
runs=()
for task_index in 0 1 2; do task="${tasks[${task_index}]}"; job="${jobs[${task_index}]}"; for index in $(seq 0 104); do setting="${settings[${index}]}"; arm="${setting_arms[${index}]}"; seed_index="${setting_seeds[${index}]}"; seed="${seeds[${seed_index}]}"; planner_seed=$((7101 + seed_index)); summary="${ROOT}/results/acid-alternative/sensitivity/${namespace}/${task}/${setting}/${arm}/train-seed-${seed}-planner-seed-${planner_seed}-job-${job}-${index}/summary.json"; test -f "${summary}"; runs+=(--run "${task}=${setting}=${arm}=${seed}=${summary}"); done; done
mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative_diagnostics.analyze_sensitivity --analysis-role "${ANALYSIS_ROLE}" --source-manifest "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUTPUT}" "${runs[@]}"
printf '%s\n' "analysis_role=${ANALYSIS_ROLE}" "pusht_job=${PUSHT_SENSITIVITY_JOB_ID}" "reacher_job=${REACHER_SENSITIVITY_JOB_ID}" "cube_job=${CUBE_SENSITIVITY_JOB_ID}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"; sha256sum "$0" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${OUTPUT}/summary.json" "${OUTPUT}/sensitivity-rates.tsv" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
