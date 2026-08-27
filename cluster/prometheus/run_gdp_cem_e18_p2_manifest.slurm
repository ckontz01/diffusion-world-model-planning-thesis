#!/usr/bin/env bash
#SBATCH --job-name=gdp-e18-p2
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e18-p2-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e18-p2-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E18 snapshot}"
: "${E17_RUN_ROOT:?missing immutable E17 run root}"
: "${OLD_P2_ROOT:?missing immutable E14/E15 P2 root}"
: "${INPUT_AUDIT_ROOT:?missing passed E18 input-audit root}"
: "${OUTPUT_ROOT:?missing unique E18 P2 root}"
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
(cd "${INPUT_AUDIT_ROOT}" && sha256sum -c sha256.txt >/dev/null)
INPUT_AUDIT=${INPUT_AUDIT_ROOT}/INPUT-AUDIT.json
INPUT_AUDIT_SHA256=$(sha256sum "${INPUT_AUDIT}" | cut -d' ' -f1)
test ! -e "${OUT}"
mkdir -p "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_gdp_cem_e18_p2_manifest.py" \
  --task "${TASK}" --dataset "${STABLEWM}/${DATASET}" \
  --partition-manifest "${PARTITION}" \
  --old-queries "${OLD_P2_ROOT}/${TASK}/queries.tsv" \
  --old-provenance "${OLD_P2_ROOT}/${TASK}/manifest.json" \
  --e17-audit "${E17_RUN_ROOT}/analysis/ADAPTER-PREFLIGHT-AUDIT.json" \
  --input-audit "${INPUT_AUDIT}" \
  --input-audit-sha256 "${INPUT_AUDIT_SHA256}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-tsv "${OUT}/queries.tsv" --output-json "${OUT}/manifest.json"
(cd "${OUT}" && sha256sum queries.tsv manifest.json > sha256.txt && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
