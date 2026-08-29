#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-analyze
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-analyze-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-analyze-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E19 snapshot}"
: "${RUN_ROOT:?missing unique E19 run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
SAGE=${SNAPSHOT}/official-sage
OUTPUT=${RUN_ROOT}/analysis

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
(cd "${RUN_ROOT}/release-audit" && sha256sum -c sha256.txt >/dev/null)
(cd "${RUN_ROOT}/data-overlap-audit" && sha256sum -c sha256.txt >/dev/null)
(cd "${RUN_ROOT}/runtime-preflight" && sha256sum -c sha256.txt >/dev/null)
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["all_passed"] is True' "${RUN_ROOT}/runtime-preflight/RUNTIME-PREFLIGHT-AUDIT.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["all_passed"] is True' "${RUN_ROOT}/runtime-preflight/CUBE-GENERATOR-COMPAT-AUDIT.json"
test ! -e "${OUTPUT}"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export PYTHONPATH=${SNAPSHOT}:${SAGE}
"${ENV_DIR}/bin/python" "${SNAPSHOT}/analyze_gdp_cem_e19_reproduction.py" \
  --sage-root "${SAGE}" \
  --evaluation-root "${RUN_ROOT}/evaluation" \
  --release-audit-root "${RUN_ROOT}/release-audit" \
  --data-audit-root "${RUN_ROOT}/data-overlap-audit" \
  --cell-manifest "${SNAPSHOT}/E19-CELLS.tsv" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-PROTOCOL-2026-08-28.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUTPUT}"
(cd "${OUTPUT}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${OUTPUT}"
