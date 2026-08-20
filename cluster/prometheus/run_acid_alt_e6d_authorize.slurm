#!/usr/bin/env bash
#SBATCH --job-name=acid-e6d-auth
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6d-auth-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6d-auth-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E6D snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
MANIFEST_JOB_ID=297535
OUT=${ROOT}/results/acid-alternative/e6d-allgate-controls/authorization/job-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/acid_alt_e6d_allgate.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/test_acid_alt_e6d_analyzer.py"
arguments=()
for task in pusht reacher cube; do
  dir=${ROOT}/manifests/acid-alternative-v3-d2/${task}/job-${MANIFEST_JOB_ID}
  arguments+=(--d2-input "${task}" "${dir}/d2-fresh.tsv" "${dir}/provenance.json")
done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_acid_alt_e6d_authorization.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E6D-ALL-ITERATIONS-MATCHED-CONTROLS-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --e6-summary "${ROOT}/results/acid-alternative/e6-d2-quantile/analysis/job-297657/summary.json" \
  "${arguments[@]}" --output-dir "${OUT}"
sha256sum "${OUT}/authorization.json" > "${OUT}/sha256.txt"
