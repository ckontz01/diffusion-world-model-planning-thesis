#!/usr/bin/env bash
#SBATCH --job-name=acid-v3-d2-score
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-d2-score-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-d2-score-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable v3 snapshot path}"
: "${TRAIN_JOB_ID:?submit with residual training array ID}"
: "${P1_GATE_JOB_ID:?submit with P1 gate job ID}"
: "${MANIFEST_JOB_ID:?submit with fresh D2 manifest array ID}"
: "${CORE_SCORE_JOB_ID:?submit with shared-score array ID}"
: "${EXECUTE_JOB_ID:?submit with execution array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; SCORER_JOB=296631; OLD_TRUE=0; OLD_SHUFFLED=1; BASE=0 ;;
  1) TASK=reacher; SCORER_JOB=296650; OLD_TRUE=2; OLD_SHUFFLED=3; BASE=4 ;;
  2) TASK=cube; SCORER_JOB=296669; OLD_TRUE=4; OLD_SHUFFLED=5; BASE=8 ;;
  *) exit 2 ;;
esac
SHARED=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/shared-score/job-${CORE_SCORE_JOB_ID}-${SLURM_ARRAY_TASK_ID}
EXECUTION=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/execution/job-${EXECUTE_JOB_ID}-${SLURM_ARRAY_TASK_ID}
OUT=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/frozen-scores/job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-v3-score-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
arguments=(
  --residual-true "6101=${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${TASK}/true/seed-6101-job-297483-${OLD_TRUE}/summary.json"
  --residual-shuffled "6101=${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${TASK}/shuffled_action/seed-6101-job-297483-${OLD_SHUFFLED}/summary.json"
  --residual-true "6102=${ROOT}/results/acid-alternative/scorers-v3-d2/${TASK}/true/seed-6102-job-${TRAIN_JOB_ID}-$((BASE + 0))/summary.json"
  --residual-true "6103=${ROOT}/results/acid-alternative/scorers-v3-d2/${TASK}/true/seed-6103-job-${TRAIN_JOB_ID}-$((BASE + 1))/summary.json"
  --residual-shuffled "6102=${ROOT}/results/acid-alternative/scorers-v3-d2/${TASK}/shuffled_action/seed-6102-job-${TRAIN_JOB_ID}-$((BASE + 2))/summary.json"
  --residual-shuffled "6103=${ROOT}/results/acid-alternative/scorers-v3-d2/${TASK}/shuffled_action/seed-6103-job-${TRAIN_JOB_ID}-$((BASE + 3))/summary.json"
)
for offset in 0 1 2; do
  seed=$((6101 + offset))
  arguments+=(--acid "${seed}=${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-${seed}-job-${SCORER_JOB}-${offset}/best.pt")
done
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/score_acid_alt_d2_task.py" \
  --task "${TASK}" --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --trainer-source "${SNAPSHOT}/train_residual_diffusion_pilot_20260816.py" \
  --p1-gate "${ROOT}/results/acid-alternative/v3-d2/p1-gate/job-${P1_GATE_JOB_ID}/gate.json" \
  --d2-manifest "${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-${MANIFEST_JOB_ID}/d2-fresh.tsv" \
  --d2-provenance "${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-${MANIFEST_JOB_ID}/provenance.json" \
  --shared-scores "${SHARED}/candidate-scores.pt" --shared-score-manifest "${SHARED}/manifest.json" \
  --execution "${EXECUTION}/candidate-executions.h5" --execution-manifest "${EXECUTION}/manifest.json" \
  "${arguments[@]}" --batch-size 8192 --output-dir "${OUT}"
printf '%s\n' "task=${TASK}" "analysis_role=D2" "job_id=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/d2-task-scores.npz" "${OUT}/manifest.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
