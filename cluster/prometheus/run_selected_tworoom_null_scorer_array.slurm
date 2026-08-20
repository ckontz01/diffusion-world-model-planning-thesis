#!/usr/bin/env bash

#SBATCH --job-name=tworoom-selected-nulls
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --array=0-5%2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-selected-null-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-selected-null-%A_%a.err

set -euo pipefail
: "${TRUE_SCORE_JOB_ID:?submit with TRUE_SCORE_JOB_ID set to the completed TwoRoom P2 true-scorer selection job}"
: "${NULL_MAP_JOB_ID:?submit with NULL_MAP_JOB_ID set to the completed TwoRoom M2 namespace-validation job}"

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
STABLEWM_HOME="${ROOT}/data/stablewm"
M1_SCRIPT="${ROOT}/scripts/train_m1_macro_cycle_head.py"
M2_SCRIPT="${ROOT}/scripts/train_m2_diffusion_head.py"
RUNNER="${ROOT}/scripts/run_selected_tworoom_null_scorer_array.slurm"
SELECTION_DIR="${STABLEWM_HOME}/derived/scorer-audits/tworoom-v1/p2-true-selection-job-${TRUE_SCORE_JOB_ID}"
NULL_MAP_DIR="${STABLEWM_HOME}/repro/tworoom-m2-null-namespace-job-${NULL_MAP_JOB_ID}"
LATENT_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-tworoom-epoch15/p1"
STATS_DIR="${STABLEWM_HOME}/derived/latents/hi-lewm-tworoom-epoch15/p1-train-stats"
TARGET_DIR="${STABLEWM_HOME}/derived/m1-macro-targets/hi-lewm-tworoom-epoch15/p1"
PAIR_DIR="${ROOT}/manifests/partitions/tworoom-v1/scorer-pairs-seed-20260728"

EXPECTED_M1_SCRIPT_SHA256="e7baf8d66bd77d53a49164592ecdc16e9b1f50b1f86baa473467ba2de9327733"
EXPECTED_M2_SCRIPT_SHA256="f74f12c945d7542f9af0e8ea0f96247b3beb6338869ab0d0589f7b10a2f69efd"
EXPECTED_LATENT_SHA256="e67129a6fb98442ed59c36cfd5274b10db02e5c0bc5acdc8db0a276f4bb8e4ee"
EXPECTED_STATS_SHA256="228b51d6fa57f22f4ebded964448d96c3f959e3a3c958d597e7bda77ee63e59f"
EXPECTED_TARGET_SHA256="f084c25a1448682b88ede0c821a5ecea2623fbb5f321729e3b81387fb4cb5a04"
EXPECTED_PAIR_SHA256="c484bee9dd149c6cc15336b796c641ad04251a330bf5b51e890da3d9e50514bc"
EXPECTED_SUMMARY_SHA256="7ec2df8dda66ea9f8fb0b0b9457533486e7d47eea40ccf8295a31abff284e94d"
EXPECTED_CHECKPOINT_SHA256="5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"
EXPECTED_NULL_MAP_RESULT_SHA256="df409129d40db4139f48dda60760498d12fae010bfa8cf97ec74706e86ffa0ce"

for required in "${IMAGE}" "${M1_SCRIPT}" "${M2_SCRIPT}" "${RUNNER}" \
  "${SELECTION_DIR}/scores.h5" "${SELECTION_DIR}/manifest.json" "${SELECTION_DIR}/checksums.sha256" \
  "${NULL_MAP_DIR}/result.json" "${NULL_MAP_DIR}/checksums.sha256" \
  "${LATENT_DIR}/latents.h5" "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" \
  "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
  "${TARGET_DIR}/targets.h5" "${TARGET_DIR}/manifest.json" "${TARGET_DIR}/checksums.sha256" \
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom selected-null input: ${required}" >&2; exit 2; fi
done
if [[ ! -L "${LATENT_DIR}" || ! -L "${STATS_DIR}" || ! -L "${TARGET_DIR}" ]]; then
  echo "TwoRoom P1 latent, statistics, or M1 target input is not canonical" >&2
  exit 2
fi
echo "${EXPECTED_M1_SCRIPT_SHA256}  ${M1_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_M2_SCRIPT_SHA256}  ${M2_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_LATENT_SHA256}  ${LATENT_DIR}/latents.h5" | sha256sum -c -
echo "${EXPECTED_STATS_SHA256}  ${STATS_DIR}/stats.npz" | sha256sum -c -
echo "${EXPECTED_TARGET_SHA256}  ${TARGET_DIR}/targets.h5" | sha256sum -c -
echo "${EXPECTED_PAIR_SHA256}  ${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" | sha256sum -c -
echo "${EXPECTED_SUMMARY_SHA256}  ${PAIR_DIR}/scorer-pair-manifests-summary.json" | sha256sum -c -
echo "${EXPECTED_NULL_MAP_RESULT_SHA256}  ${NULL_MAP_DIR}/result.json" | sha256sum -c -
sha256sum -c "${SELECTION_DIR}/checksums.sha256" >/dev/null
sha256sum -c "${NULL_MAP_DIR}/checksums.sha256" >/dev/null
sha256sum -c "${LATENT_DIR}/checksums.sha256" >/dev/null
sha256sum -c "${STATS_DIR}/checksums.sha256" >/dev/null
sha256sum -c "${TARGET_DIR}/checksums.sha256" >/dev/null

read -r M1_WIDTH M2_WIDTH M2_SIGMA < <(
  python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["classification"]=="tworoom_p2_true_scorer_raw_score_selection" and x["environment"]=="tworoom"; print(x["M1"]["selected_width"],x["M2"]["selected_width"],x["M2"]["selected_sigma"])' "${SELECTION_DIR}/manifest.json"
)
if [[ "${M1_WIDTH}" != "256" && "${M1_WIDTH}" != "512" ]]; then echo "Invalid selected M1 width" >&2; exit 2; fi
if [[ "${M2_WIDTH}" != "512" && "${M2_WIDTH}" != "1024" ]]; then echo "Invalid selected M2 width" >&2; exit 2; fi

SEEDS=(20260728 20260729 20260730)
if (( SLURM_ARRAY_TASK_ID < 3 )); then
  METHOD="M1"
  CONDITION="permuted"
  SEED_INDEX="${SLURM_ARRAY_TASK_ID}"
  WIDTH="${M1_WIDTH}"
  SCRIPT="${M1_SCRIPT}"
else
  METHOD="M2"
  CONDITION="mismatched"
  SEED_INDEX="$((SLURM_ARRAY_TASK_ID - 3))"
  WIDTH="${M2_WIDTH}"
  SCRIPT="${M2_SCRIPT}"
fi
SEED="${SEEDS[SEED_INDEX]}"
if [[ "${METHOD}" == "M1" ]]; then
  OUTPUT_DIR="${STABLEWM_HOME}/runs/scorers/m1/tworoom-v1/permuted-width${WIDTH}-seed${SEED}-job-${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
else
  OUTPUT_DIR="${STABLEWM_HOME}/derived/scorers/m2-diffusion-tworoom-v1/mismatched/width-${WIDTH}/seed-${SEED}-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
fi
JOB_TMP="/tmp/ckontzias-tworoom-selected-null-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"

if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite TwoRoom selected-null output" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_selected_width_shuffled_or_mismatched_null"
  echo "selection_job_id=${TRUE_SCORE_JOB_ID}"
  echo "null_map_job_id=${NULL_MAP_JOB_ID}"
  echo "job_id=${SLURM_ARRAY_JOB_ID}"
  echo "array_task_id=${SLURM_ARRAY_TASK_ID}"
  echo "method=${METHOD}"
  echo "condition=${CONDITION}"
  echo "dataset_hash_namespace=tworoom"
  echo "hidden_width=${WIDTH}"
  echo "selected_m2_sigma=${M2_SIGMA}"
  echo "training_seed=${SEED}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${RUNNER}" "${SCRIPT}" \
    "${SELECTION_DIR}/manifest.json" "${SELECTION_DIR}/checksums.sha256" \
    "${NULL_MAP_DIR}/result.json" "${NULL_MAP_DIR}/checksums.sha256" \
    "${LATENT_DIR}/manifest.json" "${LATENT_DIR}/checksums.sha256" \
    "${STATS_DIR}/stats.npz" "${STATS_DIR}/manifest.json" "${STATS_DIR}/checksums.sha256" \
    "${TARGET_DIR}/targets.h5" "${TARGET_DIR}/manifest.json" "${TARGET_DIR}/checksums.sha256" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_DIR}/provenance.txt"

if [[ "${METHOD}" == "M1" ]]; then
  apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
    "${IMAGE}" /bin/bash -c '
      set -euo pipefail
      export PATH="'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
      export PYTHONNOUSERSITE=1
      export PYTHONHASHSEED="'"${SEED}"'"
      export CUBLAS_WORKSPACE_CONFIG=:4096:8
      export TMPDIR="'"${JOB_TMP}"'"
      python "'"${M1_SCRIPT}"'" \
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
        --condition permuted --seed "'"${SEED}"'" --hidden-width "'"${WIDTH}"'" \
        --device cuda --learning-rate 0.0003 --weight-decay 0.0001 \
        --batch-size 256 --max-epochs 50 --patience 10 --min-delta 0.00000001
    '
  test -s "${OUTPUT_DIR}/run/best-checkpoint.pt"
  test -s "${OUTPUT_DIR}/run/training-result.json"
else
  apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
    "${IMAGE}" /bin/bash -c '
      set -euo pipefail
      export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
      export PYTHONNOUSERSITE=1
      export PYTHONHASHSEED="'"${SEED}"'"
      export CUBLAS_WORKSPACE_CONFIG=:4096:8
      export TMPDIR="'"${JOB_TMP}"'"
      python "'"${M2_SCRIPT}"'" \
        --latent-h5 "'"${LATENT_DIR}"'/latents.h5" \
        --latent-manifest "'"${LATENT_DIR}"'/manifest.json" \
        --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
        --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
        --stats-npz "'"${STATS_DIR}"'/stats.npz" \
        --stats-manifest "'"${STATS_DIR}"'/manifest.json" \
        --output-dir "'"${OUTPUT_DIR}"'" \
        --condition mismatched --dataset-hash-namespace tworoom \
        --seed "'"${SEED}"'" --hidden-width "'"${WIDTH}"'" \
        --device cuda --learning-rate 0.0003 --weight-decay 0.0001 \
        --batch-size 256 --max-epochs 50 --patience 10 --min-delta 0.00000001
    '
  test -s "${OUTPUT_DIR}/best-checkpoint.pt"
  test -s "${OUTPUT_DIR}/training-result.json"
  grep -q '"null_hash_namespace": "tworoom"' "${OUTPUT_DIR}/training-result.json"
fi

echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
