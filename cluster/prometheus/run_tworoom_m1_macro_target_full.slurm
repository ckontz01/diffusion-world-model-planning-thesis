#!/usr/bin/env bash

#SBATCH --job-name=tworoom-m1-target-full
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m1-target-full-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m1-target-full-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
SCRIPT="${ROOT}/scripts/extract_m1_macro_targets.py"
RUNNER="${ROOT}/scripts/run_tworoom_m1_macro_target_full.slurm"
PAIR_DIR="${ROOT}/manifests/partitions/tworoom-v1/scorer-pairs-seed-20260728"
DATASET="${STABLEWM_HOME}/tworoom.h5"
CHECKPOINT="${STABLEWM_HOME}/runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15_object.ckpt"
TARGET_ROOT="${STABLEWM_HOME}/derived/m1-macro-targets/hi-lewm-tworoom-epoch15"
OUTPUT_DIR="${TARGET_ROOT}/job-${SLURM_JOB_ID}"
CANONICAL_DIR="${TARGET_ROOT}/p1"
JOB_TMP="/tmp/ckontzias-tworoom-m1-target-full-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="4587be4f42c394b4569202da23980fa6fef0211f1139b9994ac13fb58bdc3795"
EXPECTED_DATASET_SHA256="129a36aa93ea0de488d2bcc876e396de9e3907bf66c6aae6394e542ef6a6d623"
EXPECTED_CHECKPOINT_SHA256="5cfb75b6c4f49a36ad1e4a89450d888a73a013cbda84be474d128455e52288ae"
EXPECTED_PAIR_SHA256="c484bee9dd149c6cc15336b796c641ad04251a330bf5b51e890da3d9e50514bc"
EXPECTED_SUMMARY_SHA256="7ec2df8dda66ea9f8fb0b0b9457533486e7d47eea40ccf8295a31abff284e94d"

for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}" "${CHECKPOINT}" \
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom M1-target input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_DATASET_SHA256}  ${DATASET}" | sha256sum -c -
echo "${EXPECTED_CHECKPOINT_SHA256}  ${CHECKPOINT}" | sha256sum -c -
echo "${EXPECTED_PAIR_SHA256}  ${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" | sha256sum -c -
echo "${EXPECTED_SUMMARY_SHA256}  ${PAIR_DIR}/scorer-pair-manifests-summary.json" | sha256sum -c -
if [[ -e "${OUTPUT_DIR}" || -e "${CANONICAL_DIR}" ]]; then
  echo "Refusing to overwrite TwoRoom M1 targets or canonical link" >&2; exit 2
fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p1_frozen_m1_macro_target_extraction"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${RUNNER}" "${SCRIPT}" "${DATASET}" "${CHECKPOINT}" \
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
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm:'"${CODE}"'/scripts/diagnostics"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=20260728
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export TMPDIR="'"${JOB_TMP}"'"
    cd "'"${CODE}"'"
    python "'"${SCRIPT}"'" \
      --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
      --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
      --dataset-file "'"${DATASET}"'" --dataset-sha256 "'"${EXPECTED_DATASET_SHA256}"'" \
      --stablewm-home "'"${STABLEWM_HOME}"'" --dataset-name tworoom \
      --policy runs/tworoom_hierarchical_default/tworoom_hierarchical_default_epoch_15 \
      --checkpoint-file "'"${CHECKPOINT}"'" \
      --output-h5 "'"${OUTPUT_DIR}"'/targets.h5" \
      --output-json "'"${OUTPUT_DIR}"'/manifest.json" \
      --batch-size 4096 --seed 20260728
  '

test -s "${OUTPUT_DIR}/targets.h5"
test -s "${OUTPUT_DIR}/manifest.json"
grep -q '"status": "ok"' "${OUTPUT_DIR}/manifest.json"
grep -q '"source_episode_dataset": "ep_idx"' "${OUTPUT_DIR}/manifest.json"
grep -q '"written_pair_count": 417583' "${OUTPUT_DIR}/manifest.json"
grep -q '"written_pair_count": 45750' "${OUTPUT_DIR}/manifest.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
ln -s -- "${OUTPUT_DIR}" "${CANONICAL_DIR}"
