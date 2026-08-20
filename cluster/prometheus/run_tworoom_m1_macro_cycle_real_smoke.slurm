#!/usr/bin/env bash

#SBATCH --job-name=tworoom-m1-head-smoke
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m1-head-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m1-head-smoke-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/train_m1_macro_cycle_head.py"
RUNNER="${ROOT}/scripts/run_tworoom_m1_macro_cycle_real_smoke.slurm"
LATENT_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-tworoom-epoch15/p1"
STATS_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-tworoom-epoch15/p1-train-stats"
TARGET_DIR="${STABLEWM_HOME}/derived/m1-macro-targets/hi-lewm-tworoom-epoch15/p1"
PAIR_DIR="${ROOT}/manifests/partitions/tworoom-v1/scorer-pairs-seed-20260728"
OUTPUT_DIR="${STABLEWM_HOME}/repro/tworoom-m1-head-real-smoke-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-tworoom-m1-head-smoke-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="e7baf8d66bd77d53a49164592ecdc16e9b1f50b1f86baa473467ba2de9327733"
EXPECTED_CHECKPOINT_SHA256="5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"
EXPECTED_PAIR_SHA256="c484bee9dd149c6cc15336b796c641ad04251a330bf5b51e890da3d9e50514bc"
EXPECTED_SUMMARY_SHA256="7ec2df8dda66ea9f8fb0b0b9457533486e7d47eea40ccf8295a31abff284e94d"
EXPECTED_TARGET_SHA256="f084c25a1448682b88ede0c821a5ecea2623fbb5f321729e3b81387fb4cb5a04"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" \
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
  "${TARGET_DIR}/targets.h5" "${TARGET_DIR}/manifest.json" "${TARGET_DIR}/checksums.sha256" \
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom M1-head-smoke input: ${required}" >&2; exit 2; fi
done
if [[ ! -L "${LATENT_DIR}" || ! -L "${STATS_DIR}" || ! -L "${TARGET_DIR}" ]]; then
  echo "TwoRoom M1 inputs are not canonical" >&2; exit 2
fi
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_PAIR_SHA256}  ${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" | sha256sum -c -
echo "${EXPECTED_SUMMARY_SHA256}  ${PAIR_DIR}/scorer-pair-manifests-summary.json" | sha256sum -c -
echo "${EXPECTED_TARGET_SHA256}  ${TARGET_DIR}/targets.h5" | sha256sum -c -
sha256sum -c "${LATENT_DIR}/checksums.sha256"
sha256sum -c "${STATS_DIR}/checksums.sha256"
sha256sum -c "${TARGET_DIR}/checksums.sha256"
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite TwoRoom M1 head smoke" >&2; exit 2; fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_m1_macro_cycle_real_data_implementation_smoke"
  echo "excluded_from_scientific_results=true"
  echo "condition=true"
  echo "hidden_width=256"
  echo "training_seed=20260728"
  echo "train_pair_limit=4096"
  echo "validation_pair_limit=1024"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${RUNNER}" "${SCRIPT}" \
    "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" \
    "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
    "${TARGET_DIR}/targets.h5" "${TARGET_DIR}/manifest.json" "${TARGET_DIR}/checksums.sha256" \
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
    export PYTHONHASHSEED=20260728
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
      --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
      --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
      --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
      --stats-npz "'"${STATS_DIR}"'/stats.npz" \
      --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
      --macro-target-h5 "'"${TARGET_DIR}"'/targets.h5" \
      --macro-target-manifest "'"${TARGET_DIR}"'/manifest.json" \
      --world-model-checkpoint-sha256 "'"${EXPECTED_CHECKPOINT_SHA256}"'" \
      --output-dir "'"${OUTPUT_DIR}"'/run" \
      --condition true --seed 20260728 --hidden-width 256 --device cuda \
      --batch-size 256 --max-epochs 2 --patience 2 \
      --train-pair-limit 4096 --validation-pair-limit 1024 --smoke
  '

test -s "${OUTPUT_DIR}/run/best-checkpoint.pt"
test -s "${OUTPUT_DIR}/run/training-result.json"
grep -q '"status": "ok"' "${OUTPUT_DIR}/run/training-result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
