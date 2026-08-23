#!/usr/bin/env bash
#SBATCH --job-name=gdp-e14-gate-c
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=48:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-c-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e14-gate-c-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E14 Gate-C source snapshot}"
: "${GATE_C_MANIFEST:?missing frozen E14 Gate-C manifest}"
: "${GATE_C_MANIFEST_SHA256:?missing E14 Gate-C manifest hash}"
: "${GATE_C_PROVENANCE:?missing E14 Gate-C manifest provenance}"
: "${GATE_C_PROVENANCE_SHA256:?missing E14 Gate-C provenance hash}"
: "${NORMALIZED_ROOT:?missing normalized E14 training root}"
: "${GATE_B_AUDIT:?missing E14 Gate-B authorization}"
: "${GATE_B_AUDIT_SHA256:?missing E14 Gate-B audit hash}"
: "${P2_ROOT:?missing E14 frozen P2 manifest root}"
: "${EVALUATION_ROOT:?missing unique E14 Gate-C evaluation root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STABLEWM=${ROOT}/data/stablewm
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm

test "$(sha256sum "${GATE_C_MANIFEST}" | cut -d' ' -f1)" = "${GATE_C_MANIFEST_SHA256}"
test "$(sha256sum "${GATE_C_PROVENANCE}" | cut -d' ' -f1)" = "${GATE_C_PROVENANCE_SHA256}"
record=$(awk -F '\t' -v id="${SLURM_ARRAY_TASK_ID}" 'NR>1 && $1==id {print $0}' "${GATE_C_MANIFEST}")
test -n "${record}"
record=${record%$'\r'}
IFS=$'\t' read -r ARRAY_ID TASK ARM MODEL_SEED HORIZON SHARD <<< "${record}"
test "${ARRAY_ID}" = "${SLURM_ARRAY_TASK_ID}"

case "${TASK}" in
  pusht)
    DATASET_NAME=pusht_expert_train; DATASET=pusht_expert_train.h5
    POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt
    ;;
  cube)
    DATASET_NAME=ogbench/cube_single_expert; DATASET=cube_single_expert.h5
    POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt
    ;;
  *) exit 2 ;;
esac
OUT=${EVALUATION_ROOT}/${TASK}/horizon-${HORIZON}/${ARM}/seed-${MODEL_SEED}/shard-${SHARD}
JOB_TMP=/tmp/ckontzias-gdp-e14-gate-c-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
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
  TMPDIR="${JOB_TMP}" "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e14_gate_c.py" \
  --task "${TASK}" --arm "${ARM}" --model-seed "${MODEL_SEED}" \
  --horizon "${HORIZON}" --shard "${SHARD}" --code-root "${CODE}" \
  --stablewm-home "${STABLEWM}" --dataset "${STABLEWM}/${DATASET}" \
  --dataset-name "${DATASET_NAME}" --world-model-policy "${POLICY}" \
  --world-model-checkpoint "${STABLEWM}/${CHECKPOINT}" \
  --training-root "${NORMALIZED_ROOT}" --gate-b-audit "${GATE_B_AUDIT}" \
  --gate-b-audit-sha256 "${GATE_B_AUDIT_SHA256}" \
  --p2-queries "${P2_ROOT}/${TASK}/queries.tsv" \
  --p2-provenance "${P2_ROOT}/${TASK}/manifest.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E14-LONG-HORIZON-SAGE-DEVELOPMENT-PROTOCOL-2026-08-23.md" \
  --implementation-decisions "${SNAPSHOT}/ACID-ALTERNATIVE-E14-IMPLEMENTATION-DECISIONS-1-2026-08-23.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --output-dir "${OUT}"
"${ENV_DIR}/bin/python" -c 'import json,sys; x=json.load(open(sys.argv[1])); assert x["status"]=="ok" and x["claim_allowed"] is False' "${OUT}/summary.json"
(cd "${OUT}" && sha256sum episodes.tsv planner-diagnostics.jsonl summary.json > sha256.txt && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}"/* "${OUT}"
