#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-d2a-analysis
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2a-analysis-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2a-analysis-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4-D2A snapshot path}"
: "${P1_GATE_JOB_ID:?submit with E4-P1 gate job ID}"
: "${D2A_SCORE_JOB_ID:?submit with E4-D2A score array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
OUT=${ROOT}/results/acid-alternative/e4-d2a/analysis/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
arguments=()
index=0
for task in pusht reacher cube; do
  SCORE=${ROOT}/results/acid-alternative/e4-d2a/scores/${task}/job-${D2A_SCORE_JOB_ID}-${index}
  arguments+=(--task "${task}" "${SCORE}/e4-d2a-task-scores.npz" "${SCORE}/manifest.json")
  index=$((index + 1))
done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_acid_alt_e4_d2a.py" \
  --parent-protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md" \
  --implementation-freeze "${SNAPSHOT}/ACID-ALTERNATIVE-E4-D2A-IMPLEMENTATION-FREEZE-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --p1-gate "${ROOT}/results/acid-alternative/e4-p1-gate/job-${P1_GATE_JOB_ID}/summary.json" \
  "${arguments[@]}" --output-dir "${OUT}"
printf '%s\n' \
  "d2a_score_array=${D2A_SCORE_JOB_ID}" "analysis_job_id=${SLURM_JOB_ID}" \
  "analysis_role=exposed_D2_development" "protected_c1_i1_read=false" \
  > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/summary.json" "${OUT}/pool-level.tsv" "${OUT}/provenance.txt" \
  > "${OUT}/sha256.txt"
if [[ -f "${OUT}/e4-d2b-authorization.json" ]]; then
  sha256sum "${OUT}/e4-d2b-authorization.json" >> "${OUT}/sha256.txt"
fi
