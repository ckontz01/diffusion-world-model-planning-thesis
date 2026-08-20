#!/usr/bin/env bash

#SBATCH --job-name=tworoom-p1-manifests
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p1-manifests-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-p1-manifests-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CREATE_SPLIT="${ROOT}/scripts/create_p1_train_val_split.py"
CREATE_PAIRS="${ROOT}/scripts/create_scorer_pair_manifests.py"
VALIDATE_PAIRS="${ROOT}/scripts/validate_scorer_pair_manifests.py"
RUNNER="${ROOT}/scripts/run_create_tworoom_p1_scorer_manifests.slurm"
PARTITION_DIR="${ROOT}/manifests/partitions/tworoom-v1"
MASTER="${PARTITION_DIR}/episodes-seed-20260728.tsv"
P1_TSV="${PARTITION_DIR}/p1-train-val-seed-20260728.tsv"
P1_JSON="${PARTITION_DIR}/p1-train-val-seed-20260728-summary.json"
P1_STDOUT="${PARTITION_DIR}/p1-train-val-seed-20260728-generation-output.json"
PAIR_DIR="${PARTITION_DIR}/scorer-pairs-seed-20260728"
M12="${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv"
M3="${PAIR_DIR}/m3-balanced-delta1-40.tsv.gz"
SUMMARY="${PAIR_DIR}/scorer-pair-manifests-summary.json"
GENERATION="${PAIR_DIR}/generation-output.json"
VALIDATION="${PAIR_DIR}/validation.json"
PROVENANCE="${PAIR_DIR}/provenance.txt"
CHECKSUMS="${PAIR_DIR}/checksums.sha256"
JOB_TMP="/tmp/ckontzias-tworoom-p1-manifests-${SLURM_JOB_ID}"

EXPECTED_MASTER_SHA256="47971097b1979798345c298d91eb36f91a0884353789b7f8736e6a1f9e79f790"
EXPECTED_SPLIT_SCRIPT_SHA256="cd582f32463c34b0b53e30973490ee93d533fb83f60f9dc6a620afb30730d887"
EXPECTED_PAIR_SCRIPT_SHA256="73b557d244ce42e75a370e4420df876828302adc7baa70e88bb234be29c136eb"
EXPECTED_VALIDATOR_SHA256="21693714292a7bf411617748877506b654e9fbde1598b62e5d5911004d0f7498"

for required in "${IMAGE}" "${CREATE_SPLIT}" "${CREATE_PAIRS}" \
  "${VALIDATE_PAIRS}" "${RUNNER}" "${MASTER}"; do
  if [[ ! -s "${required}" ]]; then
    echo "Missing TwoRoom P1-manifest input: ${required}" >&2
    exit 2
  fi
done
echo "${EXPECTED_MASTER_SHA256}  ${MASTER}" | sha256sum -c -
echo "${EXPECTED_SPLIT_SCRIPT_SHA256}  ${CREATE_SPLIT}" | sha256sum -c -
echo "${EXPECTED_PAIR_SCRIPT_SHA256}  ${CREATE_PAIRS}" | sha256sum -c -
echo "${EXPECTED_VALIDATOR_SHA256}  ${VALIDATE_PAIRS}" | sha256sum -c -
if [[ -e "${P1_TSV}" || -e "${P1_JSON}" || -e "${P1_STDOUT}" || -e "${PAIR_DIR}" ]]; then
  echo "Refusing to overwrite frozen TwoRoom P1 or pair manifests" >&2
  exit 2
fi

mkdir -p "${PAIR_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_p1_split_and_scorer_pair_freeze"
  echo "job_id=${SLURM_JOB_ID}"
  echo "dataset_namespace=tworoom"
  echo "seed=20260728"
  echo "p1_train_fraction=0.9"
  echo "m1_m2_delta=25"
  echo "m3_delta_range=1-40"
  echo "m3_train_pairs_per_delta=2500"
  echo "m3_validation_pairs_per_delta=250"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${CREATE_SPLIT}" "${CREATE_PAIRS}" "${VALIDATE_PAIRS}" \
    "${RUNNER}" "${MASTER}"
} > "${PROVENANCE}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${CREATE_SPLIT}"'" "'"${MASTER}"'" \
      --dataset-name tworoom --seed 20260728 \
      --output-tsv "'"${P1_TSV}"'" --output-json "'"${P1_JSON}"'" \
      > "'"${P1_STDOUT}"'"
    python "'"${CREATE_PAIRS}"'" "'"${MASTER}"'" "'"${P1_TSV}"'" \
      --output-dir "'"${PAIR_DIR}"'" --dataset-name tworoom --seed 20260728 \
      --m12-delta 25 --m3-min-delta 1 --m3-max-delta 40 \
      --m3-train-per-delta 2500 --m3-val-per-delta 250 \
      > "'"${GENERATION}"'"
    python "'"${VALIDATE_PAIRS}"'" "'"${MASTER}"'" "'"${P1_TSV}"'" \
      "'"${M12}"'" "'"${M3}"'" "'"${SUMMARY}"'" \
      --m12-delta 25 --m3-min-delta 1 --m3-max-delta 40 \
      --m3-train-per-delta 2500 --m3-val-per-delta 250 \
      > "'"${VALIDATION}"'"
  '

for output in "${P1_TSV}" "${P1_JSON}" "${P1_STDOUT}" "${M12}" "${M3}" \
  "${SUMMARY}" "${GENERATION}" "${VALIDATION}"; do
  test -s "${output}"
done
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${PROVENANCE}"
sha256sum "${P1_TSV}" "${P1_JSON}" "${P1_STDOUT}" "${M12}" "${M3}" \
  "${SUMMARY}" "${GENERATION}" "${VALIDATION}" "${PROVENANCE}" > "${CHECKSUMS}"
sha256sum -c "${CHECKSUMS}"
