#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-d2b-preflight
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2b-preflight-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2b-preflight-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4-D2B snapshot path}"
: "${D2A_SNAPSHOT:?submit with immutable E4-D2A snapshot path}"
: "${D2A_ANALYSIS_JOB_ID:?submit with passing E4-D2A analysis job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
D2A_ANALYSIS_DIR=${ROOT}/results/acid-alternative/e4-d2a/analysis/job-${D2A_ANALYSIS_JOB_ID}
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256
  if grep -R "TO_BE_FROZEN" -- *.py *.md *.slurm *.sh; then
    printf 'unfrozen placeholder remains\n' >&2
    exit 1
  fi
)
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${SNAPSHOT}/test_acid_alt_e4_models.py" \
  "${SNAPSHOT}/test_acid_alt_e4_scoring.py" \
  "${SNAPSHOT}/test_acid_alt_e4_controls.py" \
  "${SNAPSHOT}/test_acid_alt_e4_d2a_analyzer.py" \
  "${SNAPSHOT}/test_acid_alt_e4_d2b_models.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  AUTH="${D2A_ANALYSIS_DIR}/e4-d2b-authorization.json" \
  ANALYSIS="${D2A_ANALYSIS_DIR}/summary.json" \
  PARENT="${SNAPSHOT}/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md" \
  D2A_FREEZE="${D2A_SNAPSHOT}/ACID-ALTERNATIVE-E4-D2A-IMPLEMENTATION-FREEZE-2026-08-16.md" \
  D2A_SOURCE="${D2A_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  D2B_FREEZE="${SNAPSHOT}/ACID-ALTERNATIVE-E4-D2B-CLOSED-LOOP-FREEZE-2026-08-16.md" \
  "${ENV_DIR}/bin/python" -c \
  'import os; from pathlib import Path; import evaluate_acid_alt_e4_d2b as m; r=m.validate_d2a_authorization(Path(os.environ["AUTH"]),Path(os.environ["ANALYSIS"]),parent_protocol=Path(os.environ["PARENT"]),d2a_implementation_freeze=Path(os.environ["D2A_FREEZE"]),d2a_source_manifest=Path(os.environ["D2A_SOURCE"])); assert m.sha256_file(Path(os.environ["D2B_FREEZE"])) == m.D2B_FREEZE_SHA256; print("E4-D2B preflight authorization and freeze: ok", r["analysis_sha256"])'
printf '%s\n' \
  "status=ok" "snapshot=${SNAPSHOT}" "d2a_analysis_job_id=${D2A_ANALYSIS_JOB_ID}" \
  "protected_c1_i1_read=false" \
  > "${ROOT}/logs/acid-e4-d2b-preflight-${SLURM_JOB_ID}.provenance"

