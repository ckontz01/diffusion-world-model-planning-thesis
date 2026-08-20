#!/usr/bin/env bash

#SBATCH --job-name=tworoom-m2-null-map
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m2-null-map-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/tworoom-m2-null-map-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
SCRIPT="${ROOT}/scripts/validate_m2_null_namespace.py"
M2_SCRIPT="${ROOT}/scripts/train_m2_diffusion_head.py"
RUNNER="${ROOT}/scripts/run_validate_tworoom_m2_null_namespace.slurm"
PAIR_DIR="${ROOT}/manifests/partitions/tworoom-v1/scorer-pairs-seed-20260728"
OUTPUT_ROOT="${ROOT}/data/stablewm/repro"
OUTPUT_DIR="${OUTPUT_ROOT}/tworoom-m2-null-namespace-job-${SLURM_JOB_ID}"
CANONICAL_DIR="${OUTPUT_ROOT}/tworoom-m2-null-namespace"
JOB_TMP="/tmp/ckontzias-tworoom-m2-null-map-${SLURM_JOB_ID}"

EXPECTED_SCRIPT_SHA256="cfdb9095b9ddf501408b99fe3ef55b09861faf8bc99f33ad30dbe90b1aa04c6e"
EXPECTED_M2_SCRIPT_SHA256="f74f12c945d7542f9af0e8ea0f96247b3beb6338869ab0d0589f7b10a2f69efd"
EXPECTED_PAIR_SHA256="c484bee9dd149c6cc15336b796c641ad04251a330bf5b51e890da3d9e50514bc"
EXPECTED_SUMMARY_SHA256="7ec2df8dda66ea9f8fb0b0b9457533486e7d47eea40ccf8295a31abff284e94d"

for required in "${IMAGE}" "${SCRIPT}" "${M2_SCRIPT}" "${RUNNER}" \
  "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
  "${PAIR_DIR}/scorer-pair-manifests-summary.json"; do
  if [[ ! -s "${required}" ]]; then echo "Missing TwoRoom M2 null-map input: ${required}" >&2; exit 2; fi
done
echo "${EXPECTED_SCRIPT_SHA256}  ${SCRIPT}" | sha256sum -c -
echo "${EXPECTED_M2_SCRIPT_SHA256}  ${M2_SCRIPT}" | sha256sum -c -
echo "${EXPECTED_PAIR_SHA256}  ${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" | sha256sum -c -
echo "${EXPECTED_SUMMARY_SHA256}  ${PAIR_DIR}/scorer-pair-manifests-summary.json" | sha256sum -c -
if [[ -e "${OUTPUT_DIR}" || -e "${CANONICAL_DIR}" ]]; then
  echo "Refusing to overwrite TwoRoom M2 null-map validation" >&2
  exit 2
fi

mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=tworoom_m2_mismatched_null_namespace_validation"
  echo "dataset_hash_namespace=tworoom"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${M2_SCRIPT}" "${RUNNER}" \
    "${PAIR_DIR}/m1-m2-all-delta25-episodes.tsv" \
    "${PAIR_DIR}/scorer-pair-manifests-summary.json"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts"
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    python "'"${SCRIPT}"'" \
      --pair-plan "'"${PAIR_DIR}"'/m1-m2-all-delta25-episodes.tsv" \
      --pair-summary "'"${PAIR_DIR}"'/scorer-pair-manifests-summary.json" \
      --dataset-hash-namespace tworoom \
      --seed 20260728 \
      --output-json "'"${OUTPUT_DIR}"'/result.json"
  '

test -s "${OUTPUT_DIR}/result.json"
grep -q '"status": "ok"' "${OUTPUT_DIR}/result.json"
grep -q '"dataset_hash_namespace": "tworoom"' "${OUTPUT_DIR}/result.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
ln -s -- "${OUTPUT_DIR}" "${CANONICAL_DIR}"
