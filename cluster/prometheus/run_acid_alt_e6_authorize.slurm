#!/usr/bin/env bash
#SBATCH --job-name=acid-e6-auth
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6-auth-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e6-auth-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E6 snapshot path}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
MANIFEST_JOB_ID=297535
OUT=${ROOT}/results/acid-alternative/e6-d2-quantile/authorization/job-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256 >/dev/null
)
test ! -e "${OUT}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/test_acid_alt_e6_quantile_models.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/test_acid_alt_e6_analyzer.py"

arguments=()
for task in pusht reacher cube; do
  dir=${ROOT}/manifests/acid-alternative-v3-d2/${task}/job-${MANIFEST_JOB_ID}
  arguments+=(--d2-input "${task}" "${dir}/d2-fresh.tsv" "${dir}/provenance.json")
done
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  SLURM_JOB_ID="${SLURM_JOB_ID}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_acid_alt_e6_authorization.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E6-QUANTILE-CONSTRAINED-CEM-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --e3-summary "${ROOT}/results/acid-alternative/e3-d2-exploratory/analysis/job-297573/summary.json" \
  --e5-summary "${ROOT}/results/acid-alternative/e5-d2-counterfactual/analysis/job-297652/summary.json" \
  "${arguments[@]}" --output-dir "${OUT}"
sha256sum "${OUT}/authorization.json" > "${OUT}/sha256.txt"
