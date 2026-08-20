#!/usr/bin/env bash
#SBATCH --job-name=acid-e5-d2-preflight
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e5-d2-preflight-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e5-d2-preflight-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E5-D2 snapshot path}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256
)
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${SNAPSHOT}/test_acid_alt_e4_models.py" \
  "${SNAPSHOT}/test_acid_alt_e4_scoring.py" \
  "${SNAPSHOT}/test_acid_alt_e5_counterfactual.py" \
  "${SNAPSHOT}/test_acid_alt_e5_d2_analyzer.py"
printf '%s\n' \
  "status=ok" "snapshot=${SNAPSHOT}" \
  "analysis_role=post_outcome_exposed_D2_development" \
  "protected_c1_i1_read=false" \
  > "${ROOT}/logs/acid-e5-d2-preflight-${SLURM_JOB_ID}.provenance"
