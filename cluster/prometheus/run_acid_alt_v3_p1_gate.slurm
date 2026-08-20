#!/usr/bin/env bash
#SBATCH --job-name=acid-v3-p1-gate
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-p1-gate-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-p1-gate-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable v3 snapshot path}"
: "${TRAIN_JOB_ID:?submit with residual training array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
OUT_DIR=${ROOT}/results/acid-alternative/v3-d2/p1-gate/job-${SLURM_JOB_ID}
OUT=${OUT_DIR}/gate.json
test ! -e "${OUT_DIR}"
mkdir -p "${OUT_DIR}"
arguments=(--protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output "${OUT}")
for task in pusht reacher cube; do
  case "${task}" in
    pusht) old_true=0; old_shuffled=1; base=0 ;;
    reacher) old_true=2; old_shuffled=3; base=4 ;;
    cube) old_true=4; old_shuffled=5; base=8 ;;
  esac
  arguments+=(--entry "${task}" true 6101 "${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${task}/true/seed-6101-job-297483-${old_true}/summary.json")
  arguments+=(--entry "${task}" shuffled_action 6101 "${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${task}/shuffled_action/seed-6101-job-297483-${old_shuffled}/summary.json")
  arguments+=(--entry "${task}" true 6102 "${ROOT}/results/acid-alternative/scorers-v3-d2/${task}/true/seed-6102-job-${TRAIN_JOB_ID}-$((base + 0))/summary.json")
  arguments+=(--entry "${task}" true 6103 "${ROOT}/results/acid-alternative/scorers-v3-d2/${task}/true/seed-6103-job-${TRAIN_JOB_ID}-$((base + 1))/summary.json")
  arguments+=(--entry "${task}" shuffled_action 6102 "${ROOT}/results/acid-alternative/scorers-v3-d2/${task}/shuffled_action/seed-6102-job-${TRAIN_JOB_ID}-$((base + 2))/summary.json")
  arguments+=(--entry "${task}" shuffled_action 6103 "${ROOT}/results/acid-alternative/scorers-v3-d2/${task}/shuffled_action/seed-6103-job-${TRAIN_JOB_ID}-$((base + 3))/summary.json")
done
set +e
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/aggregate_acid_alt_v3_p1_gate.py" "${arguments[@]}"
status=$?
set -e
printf '%s\n' "training_array=${TRAIN_JOB_ID}" "gate_job_id=${SLURM_JOB_ID}" "exit_status=${status}" "protected_c1_i1_read=false" > "${OUT_DIR}/provenance.txt"
test -f "${OUT}"
sha256sum "${OUT}" "${OUT_DIR}/provenance.txt" > "${OUT_DIR}/sha256.txt"
exit "${status}"
