#!/usr/bin/env bash

# Direct simulator probe for the released PushT _set_state semantics.

#SBATCH --job-name=pusht-reset-probe
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-reset-probe-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-reset-probe-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
SCRIPT="${ROOT}/scripts/probe_pusht_reset_state.py"
RUNNER="${ROOT}/scripts/run_probe_pusht_reset_state.slurm"
DATA="${ROOT}/data/stablewm"
DATASET="${DATA}/pusht_expert_train.h5"
OUTPUT_DIR="${DATA}/derived/lineage-audits/pusht-v1/reset-probe-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-pusht-reset-probe-${SLURM_JOB_ID}"

ROOTS=(
  "${DATA}/derived/candidate-executions/pusht-v1/p2-stratum3-job-294652"
  "${DATA}/derived/candidate-executions/pusht-v1/p2-real-frame-job-294659"
  "${DATA}/derived/candidate-executions/pusht-v1/p3-stratum3-job-295104"
  "${DATA}/derived/candidate-executions/pusht-v1/p3-real-frame-job-295098"
)
for required in "${IMAGE}" "${SCRIPT}" "${RUNNER}" "${DATASET}" "${ROOTS[@]}"; do
  if [[ ! -e "${required}" ]]; then echo "Missing required input: ${required}" >&2; exit 2; fi
done
if [[ -e "${OUTPUT_DIR}" ]]; then echo "Refusing to overwrite: ${OUTPUT_DIR}" >&2; exit 2; fi
mkdir -p "${OUTPUT_DIR}" "${JOB_TMP}/xdg"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

{
  echo "classification=pusht_released_set_state_internal_offset_probe"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "${SCRIPT}" "${RUNNER}"
} > "${OUTPUT_DIR}/provenance.txt"

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONHASHSEED=20260728
    export TMPDIR="'"${JOB_TMP}"'"
    export XDG_RUNTIME_DIR="'"${JOB_TMP}"'/xdg"
    export SDL_VIDEODRIVER=dummy
    export SDL_AUDIODRIVER=dummy
    export MPLBACKEND=Agg
    python "'"${SCRIPT}"'" \
      --dataset "'"${DATASET}"'" \
      --execution-root "'"${ROOTS[0]}"'" \
      --execution-root "'"${ROOTS[1]}"'" \
      --execution-root "'"${ROOTS[2]}"'" \
      --execution-root "'"${ROOTS[3]}"'" \
      --output-json "'"${OUTPUT_DIR}"'/probe.json"
  '

test -s "${OUTPUT_DIR}/probe.json"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${OUTPUT_DIR}/provenance.txt"
find "${OUTPUT_DIR}" -type f ! -name checksums.sha256 -print0 | sort -z | xargs -0 sha256sum > "${OUTPUT_DIR}/checksums.sha256"
sha256sum -c "${OUTPUT_DIR}/checksums.sha256"
