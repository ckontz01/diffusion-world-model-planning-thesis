#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-d2a-score
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2a-score-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2a-score-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4-D2A snapshot path}"
: "${CONTROLS_JOB_ID:?submit with inverse-controls array ID}"
: "${P1_GATE_JOB_ID:?submit with E4-P1 gate job ID}"
: "${P1_TRAIN_JOB_ID:?submit with E4-P1 training array ID}"
: "${LEGACY_MANIFEST_JOB_ID:?submit with legacy D2 manifest job ID}"
: "${LEGACY_SHARED_JOB_ID:?submit with legacy D2 shared-score job ID}"
: "${LEGACY_EXECUTION_JOB_ID:?submit with legacy D2 execution job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; SCORER_JOB=296631; E4_TRUE=0; E4_SHUFFLED=1; CONTROL_BASE=0 ;;
  1) TASK=reacher; SCORER_JOB=296650; E4_TRUE=2; E4_SHUFFLED=3; CONTROL_BASE=2 ;;
  2) TASK=cube; SCORER_JOB=296669; E4_TRUE=4; E4_SHUFFLED=5; CONTROL_BASE=4 ;;
  *) exit 2 ;;
esac
SHARED=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/shared-score/job-${LEGACY_SHARED_JOB_ID}-${SLURM_ARRAY_TASK_ID}
EXECUTION=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/execution/job-${LEGACY_EXECUTION_JOB_ID}-${SLURM_ARRAY_TASK_ID}
OUT=${ROOT}/results/acid-alternative/e4-d2a/scores/${TASK}/job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-e4-d2a-score-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
arguments=()
for offset in 0 1 2; do
  seed=$((6101 + offset))
  arguments+=(--acid "${seed}=${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-${seed}-job-${SCORER_JOB}-${offset}/best.pt")
done
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" /usr/bin/env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/score_acid_alt_e4_d2a_task.py" \
  --task "${TASK}" \
  --parent-protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md" \
  --implementation-freeze "${SNAPSHOT}/ACID-ALTERNATIVE-E4-D2A-IMPLEMENTATION-FREEZE-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --p1-gate "${ROOT}/results/acid-alternative/e4-p1-gate/job-${P1_GATE_JOB_ID}/summary.json" \
  --legacy-d2-manifest "${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-${LEGACY_MANIFEST_JOB_ID}/d2-fresh.tsv" \
  --legacy-d2-provenance "${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-${LEGACY_MANIFEST_JOB_ID}/provenance.json" \
  --shared-scores "${SHARED}/candidate-scores.pt" \
  --shared-score-manifest "${SHARED}/manifest.json" \
  --execution "${EXECUTION}/candidate-executions.h5" \
  --execution-manifest "${EXECUTION}/manifest.json" \
  --e4-true-summary "${ROOT}/results/acid-alternative/e4-p1/${TASK}/true_successor/seed-7101-job-${P1_TRAIN_JOB_ID}-${E4_TRUE}/summary.json" \
  --e4-shuffled-summary "${ROOT}/results/acid-alternative/e4-p1/${TASK}/shuffled_successor/seed-7101-job-${P1_TRAIN_JOB_ID}-${E4_SHUFFLED}/summary.json" \
  --deterministic-summary "${ROOT}/results/acid-alternative/e4-d2a/controls/${TASK}/deterministic/seed-7101-job-${CONTROLS_JOB_ID}-${CONTROL_BASE}/summary.json" \
  --gaussian-summary "${ROOT}/results/acid-alternative/e4-d2a/controls/${TASK}/gaussian/seed-7101-job-${CONTROLS_JOB_ID}-$((CONTROL_BASE + 1))/summary.json" \
  "${arguments[@]}" --batch-size 8192 --output-dir "${OUT}"
printf '%s\n' \
  "task=${TASK}" "job_id=${SLURM_JOB_ID}" "controls_job_id=${CONTROLS_JOB_ID}" \
  "p1_gate_job_id=${P1_GATE_JOB_ID}" "analysis_role=exposed_D2_development" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/e4-d2a-task-scores.npz" "${OUT}/manifest.json" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
