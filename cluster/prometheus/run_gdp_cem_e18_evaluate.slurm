#!/usr/bin/env bash
#SBATCH --job-name=gdp-e18-eval
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --array=0-239%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e18-eval-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e18-eval-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E18 snapshot}"
: "${E15_TRAINING_ROOT:?missing immutable E15 training root}"
: "${E17_RUN_ROOT:?missing immutable E17 run root}"
: "${INPUT_AUDIT_ROOT:?missing passed E18 input-audit root}"
: "${P2_ROOT:?missing complete E18 P2 root}"
: "${EVALUATION_ROOT:?missing unique E18 evaluation root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM=${ROOT}/data/stablewm
CELL_MANIFEST=${SNAPSHOT}/E18-CELLS.tsv
record=$(awk -F '\t' -v id="${SLURM_ARRAY_TASK_ID}" 'NR>1 && $1==id {print $0}' "${CELL_MANIFEST}")
test -n "${record}"
IFS=$'\t' read -r ARRAY_ID TASK ARM REPLICATE LEARNED_SEED HORIZON SHARD <<< "${record}"
test "${ARRAY_ID}" = "${SLURM_ARRAY_TASK_ID}"
test "${LEARNED_SEED}" = "$((7200 + REPLICATE))"
case "${TASK}" in
  pusht)
    DATASET=pusht_expert_train.h5; DATASET_NAME=pusht_expert_train
    POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt
    ;;
  cube)
    DATASET=cube_single_expert.h5; DATASET_NAME=ogbench/cube_single_expert
    POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt
    ;;
  *) exit 2 ;;
esac
case "${ARM}" in
  vad_greedy_300|vad_greedy_576|vad_continuation|diagonal_gaussian_continuation|direct_gmm_continuation) ;;
  *) exit 2 ;;
esac
case "${HORIZON}" in 75|150) ;; *) exit 2 ;; esac
case "${SHARD}" in 0|1|2|3) ;; *) exit 2 ;; esac
OUT=${EVALUATION_ROOT}/${TASK}/${ARM}/replicate-${REPLICATE}/horizon-${HORIZON}/shard-${SHARD}
JOB_TMP=/tmp/ckontzias-gdp-e18-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${INPUT_AUDIT_ROOT}" && sha256sum -c sha256.txt >/dev/null)
(cd "${P2_ROOT}/${TASK}" && sha256sum -c sha256.txt >/dev/null)
INPUT_AUDIT=${INPUT_AUDIT_ROOT}/INPUT-AUDIT.json
INPUT_AUDIT_SHA256=$(sha256sum "${INPUT_AUDIT}" | cut -d' ' -f1)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e18.py" \
  --task "${TASK}" --arm "${ARM}" --replicate "${REPLICATE}" \
  --horizon "${HORIZON}" --shard "${SHARD}" --code-root "${CODE}" \
  --stablewm-home "${STABLEWM}" --dataset "${STABLEWM}/${DATASET}" \
  --dataset-name "${DATASET_NAME}" --world-model-policy "${POLICY}" \
  --world-model-checkpoint "${STABLEWM}/${CHECKPOINT}" \
  --e15-training-root "${E15_TRAINING_ROOT}" \
  --e17-model-root "${E17_RUN_ROOT}/models" \
  --input-audit "${INPUT_AUDIT}" --input-audit-sha256 "${INPUT_AUDIT_SHA256}" \
  --p2-queries "${P2_ROOT}/${TASK}/queries.tsv" \
  --p2-provenance "${P2_ROOT}/${TASK}/manifest.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E18-EXPLORATORY-CONTINUATION-PLANNER-PROTOCOL-2026-08-27.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
/usr/bin/python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["claim_allowed"] is False and x["d5_read"] is False' "${OUT}/summary.json"
(cd "${OUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
