#!/usr/bin/env bash
#SBATCH --job-name=acid-v3-stage-a
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-stage-a-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-stage-a-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable v3 snapshot path}"
: "${P1_GATE_JOB_ID:?submit with P1 gate job ID}"
: "${D2_SCORE_JOB_ID:?submit with D2 task-score array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
OUT=${ROOT}/results/acid-alternative/v3-d2/stage-a/analysis/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
arguments=()
index=0
for task in pusht reacher cube; do
  SCORE=${ROOT}/results/acid-alternative/v3-d2/stage-a/${task}/frozen-scores/job-${D2_SCORE_JOB_ID}-${index}
  arguments+=(--task "${task}" "${SCORE}/d2-task-scores.npz" "${SCORE}/manifest.json")
  index=$((index + 1))
done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_acid_alt_d2_stage_a.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --p1-gate "${ROOT}/results/acid-alternative/v3-d2/p1-gate/job-${P1_GATE_JOB_ID}/gate.json" \
  "${arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "d2_score_array=${D2_SCORE_JOB_ID}" "analysis_job_id=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/manifest.json" "${OUT}/pool-level.tsv" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
if [[ -f "${OUT}/stage-b-authorization.json" ]]; then sha256sum "${OUT}/stage-b-authorization.json" >> "${OUT}/sha256.txt"; fi
