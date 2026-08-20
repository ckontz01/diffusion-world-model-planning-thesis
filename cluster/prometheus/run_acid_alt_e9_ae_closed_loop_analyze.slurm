#!/usr/bin/env bash
#SBATCH --job-name=acid-e9-ae-an
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=06:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e9-ae-an-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e9-ae-an-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E9 snapshot}"
: "${E9_ARRAY_JOB_ID:?missing E9 evaluation array job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
tasks=(pusht reacher cube)
arms=(b0 acid forward ae ae_shuffled)
arguments=()
for task_index in 0 1 2; do
  task=${tasks[${task_index}]}
  for arm_index in 0 1 2 3 4; do
    arm=${arms[${arm_index}]}
    for seed_offset in 0 1 2; do
      scorer_seed=$((6101 + seed_offset)); planner_seed=$((8301 + seed_offset))
      array_index=$((task_index * 15 + arm_index * 3 + seed_offset))
      summary=${ROOT}/results/acid-alternative/e9-ae-exposed-d2/${task}/${arm}/scorer-seed-${scorer_seed}-planner-seed-${planner_seed}-job-${E9_ARRAY_JOB_ID}-${array_index}/summary.json
      arguments+=(--run "${task}" "${arm}" "${scorer_seed}" "${planner_seed}" "${summary}")
    done
  done
done
OUT=${ROOT}/results/acid-alternative/e9-ae-exposed-d2/analysis/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_acid_alt_e9_ae_closed_loop.py" \
  --method-protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" \
  --e9-protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E9-AE-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" "${arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "study=acid_alt_e9_ae_exposed_d2" "evaluation_array=${E9_ARRAY_JOB_ID}" \
  "analysis_job=${SLURM_JOB_ID}" "d2_read=true" "d3_read=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/manifest.json" "${OUT}/runs.tsv" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"

