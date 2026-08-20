#!/usr/bin/env bash
#SBATCH --job-name=gdp-e12-native
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --array=0-11%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-native-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e12-native-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E12 Stage-A snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
PRISM=${ROOT}/downloads/prism-jepa-baa0eb95
task_index=$((SLURM_ARRAY_TASK_ID / 6))
within_task=$((SLURM_ARRAY_TASK_ID % 6))
mode_index=$((within_task / 3))
seed_index=$((within_task % 3))
case "${task_index}" in
  0) TASK=pusht; DATASET=pusht_expert_train.h5; DATASET_LINK=pusht_expert_train.h5; BUNDLE=prism-hf-pusht-40461a2269da322c ;;
  1) TASK=cube; DATASET=cube_single_expert.h5; DATASET_LINK=ogbench/cube_single_expert.h5; BUNDLE=prism-hf-cube-6da8f34ef31bf25b ;;
  *) exit 2 ;;
esac
MODES=(none pog)
SEEDS=(0 1 42)
MODE=${MODES[${mode_index}]}
SEED=${SEEDS[${seed_index}]}
OUT=${ROOT}/results/acid-alternative/gdp-cem-e12/stage-a/${TASK}/${MODE}/seed-${SEED}
JOB_TMP=/tmp/ckontzias-gdp-e12-native-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
CACHE=${JOB_TMP}/stablewm
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT%/*}" "${JOB_TMP}/apptainer" "${CACHE}/${TASK}" "${CACHE}/ogbench"
ln -s "${ROOT}/data/stablewm/${DATASET}" "${CACHE}/${DATASET_LINK}"
ln -s "${ROOT}/downloads/${BUNDLE}/lewm_object.ckpt" "${CACHE}/${TASK}/lewm_object.ckpt"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" env PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${PRISM}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED="${SEED}" CUBLAS_WORKSPACE_CONFIG=:4096:8 HDF5_USE_FILE_LOCKING=FALSE \
  MUJOCO_GL=egl TMPDIR="${JOB_TMP}" SLURM_JOB_ID="${SLURM_JOB_ID}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e12_stage_a_native.py" \
  --task "${TASK}" --mode "${MODE}" --seed "${SEED}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E12-PRISM-MATCHED-UNTOUCHED-D4-PROTOCOL-2026-08-20.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --prism-reference "${PRISM}" --bundle-root "${ROOT}/downloads/${BUNDLE}" \
  --cache-root "${CACHE}" --dataset "${ROOT}/data/stablewm/${DATASET}" \
  --output-dir "${OUT}"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["status"] == "ok"' "${OUT}/summary.json"
sha256sum "${OUT}/summary.json" "${OUT}/starts.tsv" > "${OUT}/sha256.txt"
