#!/usr/bin/env bash
#SBATCH --job-name=acid-e5-d2-score
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e5-d2-score-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e5-d2-score-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E5-D2 snapshot path}"
: "${E4_D2A_SCORE_JOB_ID:?submit with completed E4-D2A score array ID}"
: "${E4_P1_TRAIN_JOB_ID:?submit with completed E4-P1 training array ID}"
: "${LEGACY_SHARED_JOB_ID:?submit with completed shared-score array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; E4_TRUE=0; E4_SHUFFLED=1 ;;
  1) TASK=reacher; E4_TRUE=2; E4_SHUFFLED=3 ;;
  2) TASK=cube; E4_TRUE=4; E4_SHUFFLED=5 ;;
  *) exit 2 ;;
esac
SHARED=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/shared-score/job-${LEGACY_SHARED_JOB_ID}-${SLURM_ARRAY_TASK_ID}
E4_D2A=${ROOT}/results/acid-alternative/e4-d2a/scores/${TASK}/job-${E4_D2A_SCORE_JOB_ID}-${SLURM_ARRAY_TASK_ID}
OUT=${ROOT}/results/acid-alternative/e5-d2-counterfactual/scores/${TASK}/job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-e5-d2-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" /usr/bin/env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/score_acid_alt_e5_d2_counterfactual.py" \
  --task "${TASK}" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --shared-scores "${SHARED}/candidate-scores.pt" \
  --shared-score-manifest "${SHARED}/manifest.json" \
  --e4-d2a-scores "${E4_D2A}/e4-d2a-task-scores.npz" \
  --e4-d2a-manifest "${E4_D2A}/manifest.json" \
  --e4-true-summary "${ROOT}/results/acid-alternative/e4-p1/${TASK}/true_successor/seed-7101-job-${E4_P1_TRAIN_JOB_ID}-${E4_TRUE}/summary.json" \
  --e4-shuffled-summary "${ROOT}/results/acid-alternative/e4-p1/${TASK}/shuffled_successor/seed-7101-job-${E4_P1_TRAIN_JOB_ID}-${E4_SHUFFLED}/summary.json" \
  --batch-size 8192 --output-dir "${OUT}"
printf '%s\n' \
  "task=${TASK}" "job_id=${SLURM_JOB_ID}" \
  "analysis_role=post_outcome_exposed_D2_development" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/e5-counterfactual-scores.npz" "${OUT}/manifest.json" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
