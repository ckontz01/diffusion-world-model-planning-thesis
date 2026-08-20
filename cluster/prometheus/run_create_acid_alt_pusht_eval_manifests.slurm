#!/usr/bin/env bash

#SBATCH --job-name=acid-alt-pusht-manifests
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-manifests-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-manifests-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
DATASET="${ROOT}/data/stablewm/pusht_expert_train.h5"
PARTITIONS="${ROOT}/manifests/partitions/pusht-v1/episodes-seed-20260728.tsv"
OUTPUT="${ROOT}/manifests/acid-alternative-v1/pusht"

test -f "${DATASET}"
test -f "${PARTITIONS}"
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  "${IMAGE}" env \
  PYTHONPATH="${ROOT}/scripts" \
  "${ENV_DIR}/bin/python" -m acid_alternative.create_eval_manifests \
    --dataset "${DATASET}" \
    --task pusht \
    --partition-manifest "${PARTITIONS}" \
    --legacy-root "${ROOT}/data/stablewm/repro" \
    --legacy-root "${ROOT}/data/stablewm/derived/candidate-pools/pusht-v1" \
    --legacy-root "${ROOT}/data/stablewm/derived/candidate-executions/pusht-v1" \
    --legacy-root "${ROOT}/data/stablewm/derived/closed-loop-confirmation/pusht-v1" \
    --legacy-root "${ROOT}/candidate-results" \
    --legacy-exclude-path-token cube \
    --legacy-exclude-path-token reacher \
    --legacy-exclude-path-token tworoom \
    --goal-offset 25 \
    --output-dir "${OUTPUT}"

sha256sum "${OUTPUT}"/*.tsv "${OUTPUT}/summary.json" > "${OUTPUT}/sha256.txt"
