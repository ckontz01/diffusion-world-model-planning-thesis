#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-release
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-release-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-release-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E19 snapshot}"
: "${RUN_ROOT:?missing unique E19 run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
SAGE=${SNAPSHOT}/official-sage
CHECKPOINTS=${RUN_ROOT}/checkpoints
OUTPUT=${RUN_ROOT}/release-audit

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
(cd "${RUN_ROOT}/preparation" && sha256sum -c sha256.txt >/dev/null)
test ! -e "${OUTPUT}"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export PYTHONPATH=${SNAPSHOT}:${SAGE}
"${ENV_DIR}/bin/python" "${SNAPSHOT}/audit_gdp_cem_e19_release.py" \
  --sage-root "${SAGE}" \
  --checkpoint-root "${CHECKPOINTS}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-PROTOCOL-2026-08-28.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUTPUT}"
(cd "${OUTPUT}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${OUTPUT}"
