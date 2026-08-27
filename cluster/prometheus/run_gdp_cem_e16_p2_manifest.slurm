#!/usr/bin/env bash
#SBATCH --job-name=gdp-e16-p2-manifest
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e16-p2-manifest-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e16-p2-manifest-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E16 Stage-C snapshot}"
: "${STAGE_B_AUDIT:?missing passed E16 Stage-B audit}"
: "${OLD_P2_ROOT:?missing immutable E14/E15 P2 root}"
: "${OUTPUT_ROOT:?missing unique E16 P2 manifest root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
STABLEWM=${ROOT}/data/stablewm
case "${SLURM_ARRAY_TASK_ID}" in
  0)
    TASK=pusht; DATASET=pusht_expert_train.h5
    PARTITION=${ROOT}/manifests/partitions/pusht-v1/episodes-seed-20260728.tsv
    ;;
  1)
    TASK=cube; DATASET=cube_single_expert.h5
    PARTITION=${ROOT}/manifests/partitions/cube-v1/episodes-seed-20260728.tsv
    ;;
  *) exit 2 ;;
esac
OUT=${OUTPUT_ROOT}/${TASK}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_gdp_cem_e16_p2_manifest.py" \
  --task "${TASK}" --dataset "${STABLEWM}/${DATASET}" \
  --partition-manifest "${PARTITION}" \
  --old-queries "${OLD_P2_ROOT}/${TASK}/queries.tsv" \
  --old-provenance "${OLD_P2_ROOT}/${TASK}/manifest.json" \
  --stage-b-audit "${STAGE_B_AUDIT}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E16-CONTINUATION-AWARE-DIRECT-VAD-DEVELOPMENT-PROTOCOL-2026-08-27.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-tsv "${OUT}/queries.tsv" --output-json "${OUT}/manifest.json"
(cd "${OUT}" && sha256sum queries.tsv manifest.json > sha256.txt && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"

