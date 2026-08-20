#!/usr/bin/env bash

# Unit-test the immutable diagnostic snapshot before any outcome analysis.

#SBATCH --job-name=acid-alt-diag-preflight
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-diag-preflight-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-diag-preflight-%j.err

set -euo pipefail
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
OUTPUT="${ROOT}/results/acid-alternative/preflight/diagnostics/job-${SLURM_JOB_ID}"
for required in "${IMAGE}" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256"; do test -f "${required}"; done
for snapshot in "${CORE_SNAPSHOT}" "${DIAG_SNAPSHOT}"; do
  (cd "${snapshot}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi
mkdir -p "${OUTPUT}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  python -m pytest -q -p no:cacheprovider \
  "${DIAG_SNAPSHOT}/acid_alternative_diagnostics/tests" > "${OUTPUT}/unit-tests.txt"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 "${ENV_DIR}/bin/python" - \
  "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  "${OUTPUT}/unit-tests.txt" "${OUTPUT}/gate.json" <<'PYTHON'
import hashlib, json, pathlib, sys
def digest(path):
    value=hashlib.sha256()
    with open(path,"rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""): value.update(block)
    return value.hexdigest()
core, diag, tests, output=sys.argv[1:]
pathlib.Path(output).write_text(json.dumps({"status":"pass","kind":"acid_alternative_diagnostic_preflight_v1","core_manifest_sha256":digest(core),"diagnostic_manifest_sha256":digest(diag),"unit_tests_sha256":digest(tests)},indent=2,sort_keys=True)+"\n",encoding="utf-8")
PYTHON
printf '%s\n' "job_id=${SLURM_JOB_ID}" "node=$(hostname)" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${OUTPUT}/unit-tests.txt" "${OUTPUT}/gate.json" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
