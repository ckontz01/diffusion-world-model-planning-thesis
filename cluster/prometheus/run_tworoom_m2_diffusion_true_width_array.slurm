#!/usr/bin/env bash

#SBATCH --job-name=tworoom-m2-widths
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --array=0-5%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m2-width-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m2-width-%A_%a.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/train_m2_diffusion_head.py"
RUNNER="${ROOT}/scripts/run_tworoom_m2_diffusion_true_width_array.slurm"
LATENT_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-tworoom-epoch15/p1"
STATS_DIR="${ROOT}/data/stablewm/derived/latents/hi-lewm-tworoom-epoch15/p1-train-stats"
PAIR_DIR="${ROOT}/manifests/partitions/tworoom-v1/scorer-pairs-seed-20260728"

EXPECTED_SCRIPT_SHA256="10e54d38d0d8f318eb53b0c21ce50933ef3b8d7b922d21a1132ea8d8723de521"
EXPECTED_PAIR_SHA256="c484bee9dd149c6cc15336b796c641ad04251a330bf5b51e890da3d9e50514bc"
EXPECTED_SUMMARY_SHA256="7ec2df8dda66ea9f8fb0b0b9457533486e7d47eea40ccf8295a31abff284e94d"

SEEDS=(20260728 20260729 20260730)
if (( SLURM_ARRAY_TASK_ID < 3 )); then
  WIDTH=512
  SEED_INDEX="${SLURM_ARRAY_TASK_ID}"
else
  WIDTH=1024
  SEED_INDEX="$((SLURM_ARRAY_TASK_ID - 3))"
fi
TRAINING_SEED="${SEEDS[SEED_INDEX]}"
OUTPUT_DIR="${ROOT}/data/stablewm/derived/scorers/m2-diffusion-tworoom-v1/true/width-${WIDTH}/seed-${TRAINING_SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-m2-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" \
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom M2 input: ${required}" >&2; exit 2; fi
done
if [[ ! -L "${LATENT_DIR}" || ! -L "${STATS_DIR}" ]]; then
  echo "TwoRoom P1 cache or statistics are not canonical" >&2; exit 2
fi
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_PAIR_SHA256}  ${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" | sha256sum -c -
echo "${EXPECTED_SUMMARY_SHA256}  ${PAIR_DIR}/scorer-pair-manifests-summary.json" | sha256sum -c -
sha256sum -c "${LATENT_DIR}/checksums.sha256"
sha256sum -c "${STATS_DIR}/checksums.sha256"
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite TwoRoom M2 output" >&2; exit 2; fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_m2_true_width_development_training"
  echo "condition=true"
  echo "hidden_width=${WIDTH}"
  echo "training_seed=${TRAINING_SEED}"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${RUNNER}" "${SCRIPT}" \
    "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" \
    "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED="'"${TRAINING_SEED}"'"
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
      --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
      --stats-npz "'"${STATS_DIR}"'/stats.npz" \
      --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --output-dir "'"${OUTPUT_DIR}"'" \
      --condition true --seed "'"${TRAINING_SEED}"'" \
      --hidden-width "'"${WIDTH}"'" --device cuda
  '

test -s "${OUTPUT_DIR}/best-checkpoint.pt"
test -s "${OUTPUT_DIR}/training-result.json"
grep -q '"status": "ok"' "${OUTPUT_DIR}/training-result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
