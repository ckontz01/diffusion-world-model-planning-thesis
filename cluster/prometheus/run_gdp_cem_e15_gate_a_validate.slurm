#!/usr/bin/env bash
#SBATCH --job-name=gdp-e15-gate-a
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-gate-a-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-gate-a-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E15 offline snapshot}"
: "${SMOKE_ROOT:?missing complete E15 smoke root}"
: "${SAGE_NORMALIZED_ROOT:?missing normalized E14 SAGE root}"
: "${GATE_A_ROOT:?missing unique E15 Gate-A output root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${GATE_A_ROOT}"
mkdir -p "${GATE_A_ROOT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/validate_gdp_cem_e15_gate_a.py" \
  --smoke-root "${SMOKE_ROOT}" --sage-normalized-root "${SAGE_NORMALIZED_ROOT}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --static-preflight "${SNAPSHOT}/E15-OFFLINE-STATIC-PREFLIGHT-PASSED.json" \
  --output-dir "${GATE_A_ROOT}"
(cd "${GATE_A_ROOT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${GATE_A_ROOT}"/* "${GATE_A_ROOT}"
