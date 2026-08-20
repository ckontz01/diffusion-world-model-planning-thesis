#!/usr/bin/env bash
#SBATCH --job-name=acid-e5-d2-analysis
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e5-d2-analysis-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e5-d2-analysis-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E5-D2 snapshot path}"
: "${E5_SCORE_JOB_ID:?submit with completed E5-D2 score array ID}"
: "${E4_D2A_SCORE_JOB_ID:?submit with completed E4-D2A score array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
OUT=${ROOT}/results/acid-alternative/e5-d2-counterfactual/analysis/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
arguments=()
index=0
for task in pusht reacher cube; do
  E4=${ROOT}/results/acid-alternative/e4-d2a/scores/${task}/job-${E4_D2A_SCORE_JOB_ID}-${index}/e4-d2a-task-scores.npz
  E5=${ROOT}/results/acid-alternative/e5-d2-counterfactual/scores/${task}/job-${E5_SCORE_JOB_ID}-${index}/e5-counterfactual-scores.npz
  arguments+=(--task "${task}" "${E4}" "${E5}")
  index=$((index + 1))
done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_acid_alt_e5_d2_counterfactual.py" \
  "${arguments[@]}" --output "${OUT}/summary.json"
printf '%s\n' \
  "e5_score_array=${E5_SCORE_JOB_ID}" \
  "analysis_job_id=${SLURM_JOB_ID}" \
  "analysis_role=post_outcome_exposed_D2_development" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
