#!/usr/bin/env bash
#SBATCH --job-name=acid-e4-p0
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-p0-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-e4-p0-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable E4 snapshot path}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
OUT=${ROOT}/results/acid-alternative/e4-p0/job-${SLURM_JOB_ID}
JOB_TMP=/tmp/ckontzias-acid-e4-p0-${SLURM_JOB_ID}
test ! -e "${OUT}"
test ! -w "${SNAPSHOT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
(
  cd "${SNAPSHOT}"
  sha256sum --check SOURCE-MANIFEST.sha256
)
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" /usr/bin/env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=7101 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" -m pytest -q -p no:cacheprovider \
  "${SNAPSHOT}/test_acid_alt_e4_models.py"
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" /usr/bin/env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=7101 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/train_acid_alt_e4_didm.py" --self-test
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" /usr/bin/env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=7101 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/preflight_acid_alt_e4.py" \
  --task-spec "pusht=${ROOT}/data/stablewm/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/p1-flat-latents-job-296628/latents.h5=${ROOT}/data/stablewm/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/p1-flat-latents-job-296628/manifest.json=${ROOT}/data/stablewm/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/transition-cache-job-296629/transitions.h5=${ROOT}/data/stablewm/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/transition-cache-job-296629/manifest.json=${ROOT}/results/acid-alternative/scorers/pusht/acid/true/seed-6101-job-296631-0/best.pt" \
  --task-spec "reacher=${ROOT}/data/stablewm/derived/acid-alternative-v1/reacher/lewm/p1-flat-latents-job-296647/latents.h5=${ROOT}/data/stablewm/derived/acid-alternative-v1/reacher/lewm/p1-flat-latents-job-296647/manifest.json=${ROOT}/data/stablewm/derived/acid-alternative-v1/reacher/lewm/transition-cache-job-296648/transitions.h5=${ROOT}/data/stablewm/derived/acid-alternative-v1/reacher/lewm/transition-cache-job-296648/manifest.json=${ROOT}/results/acid-alternative/scorers/reacher/acid/true/seed-6101-job-296650-0/best.pt" \
  --task-spec "cube=${ROOT}/data/stablewm/derived/acid-alternative-v1/cube/lewm-hf-b0747c5/p1-flat-latents-job-296666/latents.h5=${ROOT}/data/stablewm/derived/acid-alternative-v1/cube/lewm-hf-b0747c5/p1-flat-latents-job-296666/manifest.json=${ROOT}/data/stablewm/derived/acid-alternative-v1/cube/lewm-hf-b0747c5/transition-cache-job-296667/transitions.h5=${ROOT}/data/stablewm/derived/acid-alternative-v1/cube/lewm-hf-b0747c5/transition-cache-job-296667/manifest.json=${ROOT}/results/acid-alternative/scorers/cube/acid/true/seed-6101-job-296669-0/best.pt" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E4-DIFFUSION-INVERSE-DEVELOPMENT-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output "${OUT}/gate.json"
printf '%s\n' \
  "job_id=${SLURM_JOB_ID}" \
  "snapshot=${SNAPSHOT}" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/gate.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
