#!/usr/bin/env bash
#SBATCH --job-name=gdp-e11-preflight
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e11-preflight-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e11-preflight-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E11 snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
OUT=${ROOT}/results/acid-alternative/gdp-cem-e11-preflight/job-${SLURM_JOB_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
test ! -e "${ROOT}/manifests/gdp-cem-e11-d3"
test ! -e "${ROOT}/results/acid-alternative/gdp-cem-e11-d3"
mkdir -p "${OUT}"
chmod a-w \
  "${ROOT}/data/stablewm/pusht_expert_train.h5" \
  "${ROOT}/data/stablewm/reacher.h5" \
  "${ROOT}/data/stablewm/cube_single_expert.h5" \
  "${ROOT}/data/stablewm/pusht/lewm_hf_22b330c_object.ckpt" \
  "${ROOT}/data/stablewm/reacher/lewm_object.ckpt" \
  "${ROOT}/data/stablewm/cube/lewm_hf_b0747c5_object.ckpt"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/preflight_gdp_cem_e11.py" \
  --root "${ROOT}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output "${OUT}/preflight.json"
printf '%s\n' "study=gdp_cem_e11_preflight" "job_id=${SLURM_JOB_ID}" \
  "identifier_inputs_only=true" "outcome_columns_read=false" \
  "d3_read=false" "protected_c1_i1_read=false" > "${OUT}/audit.txt"
sha256sum "${OUT}/preflight.json" "${OUT}/audit.txt" > "${OUT}/sha256.txt"
