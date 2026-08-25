#!/usr/bin/env bash
#SBATCH --job-name=gdp-e15-gate-c
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --array=0-431%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-gate-c-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e15-gate-c-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E15 Gate-C snapshot}"
: "${E15_TRAINING_ROOT:?missing immutable E15 training root}"
: "${SAGE_NORMALIZED_ROOT:?missing normalized E14 SAGE root}"
: "${GATE_A_AUDIT:?missing passed E15 Gate-A audit}"
: "${GATE_A_AUDIT_SHA256:?missing E15 Gate-A audit hash}"
: "${GATE_B_AUDIT:?missing passed E15 Gate-B audit}"
: "${GATE_B_AUDIT_SHA256:?missing E15 Gate-B audit hash}"
: "${P2_ROOT:?missing immutable identifier-only P2 root}"
: "${EVALUATION_ROOT:?missing unique E15 Gate-C output root}"

ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM=${ROOT}/data/stablewm

CELL_MANIFEST=${SNAPSHOT}/E15-GATE-C-CELLS.tsv
record=$(awk -F '\t' -v id="${SLURM_ARRAY_TASK_ID}" \
  'NR>1 && $1==id {print $0}' "${CELL_MANIFEST}")
test -n "${record}"
IFS=$'\t' read -r ARRAY_ID TASK ARM REPLICATE LEARNED_SEED SAGE_SEED HORIZON SHARD <<< "${record}"
test "${ARRAY_ID}" = "${SLURM_ARRAY_TASK_ID}"
test "${LEARNED_SEED}" = "$((7200 + REPLICATE))"
test "${SAGE_SEED}" = "$((6100 + REPLICATE))"
case "${TASK}" in
  pusht)
    TASK=pusht; DATASET=pusht_expert_train.h5; DATASET_NAME=pusht_expert_train
    POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt
    ;;
  cube)
    TASK=cube; DATASET=cube_single_expert.h5; DATASET_NAME=ogbench/cube_single_expert
    POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt
    ;;
  *) exit 2 ;;
esac
case "${ARM}" in
  base_cem|sage_reconstruction|sage_one_stage|vad|direct_gmm|diagonal_gaussian) ;;
  *) exit 2 ;;
esac
case "${HORIZON}" in
  25|75|150) ;;
  *) exit 2 ;;
esac
case "${SHARD}" in 0|1|2|3) ;; *) exit 2 ;; esac

OUT=${EVALUATION_ROOT}/${TASK}/${ARM}/replicate-${REPLICATE}/horizon-${HORIZON}/shard-${SHARD}
JOB_TMP=/tmp/ckontzias-gdp-e15-gate-c-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
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
  TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e15_gate_c.py" \
  --task "${TASK}" --arm "${ARM}" --replicate "${REPLICATE}" \
  --horizon "${HORIZON}" --shard "${SHARD}" --code-root "${CODE}" \
  --stablewm-home "${STABLEWM}" --dataset "${STABLEWM}/${DATASET}" \
  --dataset-name "${DATASET_NAME}" --world-model-policy "${POLICY}" \
  --world-model-checkpoint "${STABLEWM}/${CHECKPOINT}" \
  --e15-training-root "${E15_TRAINING_ROOT}" \
  --sage-normalized-root "${SAGE_NORMALIZED_ROOT}" \
  --gate-a-audit "${GATE_A_AUDIT}" --gate-a-audit-sha256 "${GATE_A_AUDIT_SHA256}" \
  --gate-b-audit "${GATE_B_AUDIT}" --gate-b-audit-sha256 "${GATE_B_AUDIT_SHA256}" \
  --p2-queries "${P2_ROOT}/${TASK}/queries.tsv" \
  --p2-provenance "${P2_ROOT}/${TASK}/manifest.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E15-BOUNDARY-AWARE-LONG-HORIZON-PROTOCOL-2026-08-25.md" \
  --implementation-decisions "${SNAPSHOT}/E15-IMPLEMENTATION-DECISIONS-1-2026-08-25.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"

/usr/bin/python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["claim_allowed"] is False and x["d5_read"] is False' "${OUT}/summary.json"
(cd "${OUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
