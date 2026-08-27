#!/usr/bin/env bash
#SBATCH --job-name=gdp-e17-adapter
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=12:00:00
#SBATCH --array=0-1%2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e17-adapter-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e17-adapter-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E17 snapshot}"
: "${CACHE_ROOT:?missing completed immutable E17 cache root}"
: "${OUTPUT_ROOT:?missing unique E17 adapter root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006

case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht ;;
  1) TASK=cube ;;
  *) exit 2 ;;
esac
OUT=${OUTPUT_ROOT}/${TASK}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${CACHE_ROOT}/${TASK}" && sha256sum -c sha256.txt >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}"

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONPATH="${SNAPSHOT}" \
  "${ENV_DIR}/bin/python" \
  "${SNAPSHOT}/train_gdp_cem_e17_transition_state_adapter.py" \
  --task "${TASK}" --cache-h5 "${CACHE_ROOT}/${TASK}/cache.h5" \
  --cache-manifest "${CACHE_ROOT}/${TASK}/manifest.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E17-TRANSITION-STATE-ADAPTER-PREFLIGHT-PROTOCOL-2026-08-27.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUT}"

/usr/bin/python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["validation_payload_rows_read_before_checkpoint"]==0 and x["d5_read"] is False' "${OUT}/summary.json"
(cd "${OUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
