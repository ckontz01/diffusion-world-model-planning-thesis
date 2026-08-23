#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-p2-manifest
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-p2-manifest-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-p2-manifest-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 P2-manifest snapshot}"
: "${OUTPUT_ROOT:?missing unique E14 P2-manifest output root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STABLEWM=${ROOT}/data/stablewm
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; DATASET=pusht_expert_train.h5 ;;
  1) TASK=cube; DATASET=cube_single_expert.h5 ;;
  *) exit 2 ;;
esac
PARTITIONS=${ROOT}/manifests/partitions/${TASK}-v1/episodes-seed-20260728.tsv
OUT=${OUTPUT_ROOT}/${TASK}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_gdp_cem_e14_p2_manifest.py" \
  --task "${TASK}" --dataset "${STABLEWM}/${DATASET}" \
  --partition-manifest "${PARTITIONS}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-tsv "${OUT}/queries.tsv" --output-json "${OUT}/manifest.json"
sha256sum "${OUT}/queries.tsv" "${OUT}/manifest.json" > "${OUT}/sha256.txt"
chmod a-w "${OUT}"/* "${OUT}"
