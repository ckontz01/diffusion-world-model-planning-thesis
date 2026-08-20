#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-d2a-preflight
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2a-preflight-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-d2a-preflight-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4-D2A snapshot path}"
: "${P1_GATE_JOB_ID:?submit with completed E4-P1 gate job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
test -d "${SNAPSHOT}"
test ! -w "${SNAPSHOT}"
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256
  if grep -R "TO_BE_FROZEN" -- *.py *.md; then
    printf 'unfrozen placeholder remains\n' >&2
    exit 1
  fi
)
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" -m pytest -q \
  "${SNAPSHOT}/test_acid_alt_e4_models.py" \
  "${SNAPSHOT}/test_acid_alt_e4_scoring.py" \
  "${SNAPSHOT}/test_acid_alt_e4_controls.py" \
  "${SNAPSHOT}/test_acid_alt_e4_d2a_analyzer.py"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" /usr/bin/env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  P1_GATE="${ROOT}/results/acid-alternative/e4-p1-gate/job-${P1_GATE_JOB_ID}/summary.json" \
  IMPLEMENTATION_FREEZE="${SNAPSHOT}/ACID-ALTERNATIVE-E4-D2A-IMPLEMENTATION-FREEZE-2026-08-16.md" \
  "${ENV_DIR}/bin/python" -c \
  'import os; from pathlib import Path; import score_acid_alt_e4_d2a_task as m; m.validate_p1_gate(Path(os.environ["P1_GATE"])); assert m.sha256_file(Path(os.environ["IMPLEMENTATION_FREEZE"])) == m.IMPLEMENTATION_FREEZE_SHA256; print("E4-D2A preflight gate and freeze: ok")'
printf '%s\n' \
  "status=ok" "snapshot=${SNAPSHOT}" "p1_gate_job_id=${P1_GATE_JOB_ID}" \
  "protected_c1_i1_read=false" \
  > "${ROOT}/logs/acid-e4-d2a-preflight-${SLURM_JOB_ID}.provenance"
