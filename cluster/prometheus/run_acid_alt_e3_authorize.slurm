#!/usr/bin/env bash
#SBATCH --job-name=acid-e3-authorize
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e3-authorize-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e3-authorize-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E3 snapshot path}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
STAGE_A=${ROOT}/results/acid-alternative/v3-d2/stage-a/analysis/job-297565
D2_ROOT=${ROOT}/manifests/acid-alternative-v3-d2
OUT=${ROOT}/results/acid-alternative/e3-d2-exploratory/authorization/job-${SLURM_JOB_ID}

test ! -e "${OUT}"
test "$(sha256sum "${SNAPSHOT}/ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-PROTOCOL-2026-08-16.md" | cut -d' ' -f1)" = c48eaf320c9b378af5e5d265397af8efd3485c45a288481d25f5161238af1fb0
cd "${SNAPSHOT}"
sha256sum -c SOURCE-MANIFEST.sha256
for script in \
  run_acid_alt_e3_authorize.slurm \
  run_acid_alt_e3_d2_closed_loop.slurm \
  run_acid_alt_e3_d2_analyze.slurm \
  submit_acid_alt_e3_d2.sh; do
  bash -n "${SNAPSHOT}/${script}"
done

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" - "${SNAPSHOT}" <<'PY'
from pathlib import Path
import sys

snapshot = Path(sys.argv[1])
files = (
    "create_acid_alt_e3_authorization.py",
    "preflight_acid_alt_e3.py",
    "evaluate_acid_alt_e3_d2.py",
    "analyze_acid_alt_e3_d2_closed_loop.py",
    "test_acid_alt_e3_analyzer.py",
)
for name in files:
    path = snapshot / name
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
print(f"read_only_python_compile=passed files={len(files)}")
PY

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/preflight_acid_alt_e3.py" \
  "${SNAPSHOT}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_acid_alt_e3_authorization.py" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E3-EXPLORATORY-D2-CLOSED-LOOP-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --stage-a-summary "${STAGE_A}/summary.json" \
  --stage-a-manifest "${STAGE_A}/manifest.json" \
  --d2-input pusht "${D2_ROOT}/pusht/job-297535/d2-fresh.tsv" "${D2_ROOT}/pusht/job-297535/provenance.json" \
  --d2-input reacher "${D2_ROOT}/reacher/job-297535/d2-fresh.tsv" "${D2_ROOT}/reacher/job-297535/provenance.json" \
  --d2-input cube "${D2_ROOT}/cube/job-297535/d2-fresh.tsv" "${D2_ROOT}/cube/job-297535/provenance.json" \
  --output-dir "${OUT}"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/test_acid_alt_e3_analyzer.py" \
  "${SNAPSHOT}" "${OUT}/authorization.json"

printf '%s\n' \
  "authorization_job_id=${SLURM_JOB_ID}" \
  "analysis_role=post_v3_exploratory_d2_closed_loop_development" \
  "v3_stage_b_authorized=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum \
  "${OUT}/authorization.json" \
  "${OUT}/manifest.json" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
