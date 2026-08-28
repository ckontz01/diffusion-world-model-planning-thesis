#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-sage
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=12
#SBATCH --mem=96G
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --array=0-179%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-sage-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-sage-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E19 snapshot}"
: "${RUN_ROOT:?missing unique E19 run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
SAGE=${SNAPSHOT}/official-sage
STABLEWM=${ROOT}/data/stablewm
CHECKPOINTS=${RUN_ROOT}/checkpoints
EVALUATION=${RUN_ROOT}/evaluation
CELLS=${SNAPSHOT}/E19-CELLS.tsv
JOB_TMP=/tmp/ckontzias-gdp-e19-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test -f "${SNAPSHOT}/lewm-runtime/jepa.py"
test -f "${SNAPSHOT}/lewm-runtime/module.py"
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
(cd "${RUN_ROOT}/preparation" && sha256sum -c sha256.txt >/dev/null)
(cd "${RUN_ROOT}/release-audit" && sha256sum -c sha256.txt >/dev/null)
(cd "${RUN_ROOT}/data-overlap-audit" && sha256sum -c sha256.txt >/dev/null)
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["release_gate_passed"] is True' "${RUN_ROOT}/release-audit/RELEASE-AUDIT.json"
python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["data_identity_gate_passed"] is True' "${RUN_ROOT}/data-overlap-audit/DATA-OVERLAP-AUDIT.json"
record=$(awk -F '\t' -v id="${SLURM_ARRAY_TASK_ID}" 'NR>1 && $1==id {print $0}' "${CELLS}")
test -n "${record}"
IFS=$'\t' read -r ARRAY_ID BENCHMARK METHOD SEED HORIZON <<< "${record}"
test "${ARRAY_ID}" = "${SLURM_ARRAY_TASK_ID}"
case "${METHOD}" in
  base_cem|far_goal_prior_cem|lewm_generator|generator_prior_top|sage) ;;
  *) exit 2 ;;
esac
case "${SEED}" in 32|42|52) ;; *) exit 2 ;; esac
case "${HORIZON}" in 25|50|75|100|125|150) ;; *) exit 2 ;; esac

case "${BENCHMARK}" in
  pusht)
    DATASET=${RUN_ROOT}/preparation/pusht_expert_train.lance
    LEWM=${STABLEWM}/pusht/lewm_hf_22b330c_object.ckpt
    LEWM_SHA=c3883fb585f4d97b628922a13a43441fe63e883808014d25312aca1793820659
    ;;
  cube)
    DATASET=${STABLEWM}/cube_single_expert.h5
    LEWM=${STABLEWM}/cube/lewm_hf_b0747c5_object.ckpt
    LEWM_SHA=5175b8d7a99b3c19aeee08027c666fb0562e316f14c36e74ac3a52ecce531e07
    ;;
  *) exit 2 ;;
esac
printf '%s  %s\n' "${LEWM_SHA}" "${LEWM}" | sha256sum --check --strict

GENERATOR_ARGS=()
PRIOR=${CHECKPOINTS}/${BENCHMARK}_action_prior.pt
case "${METHOD}" in
  far_goal_prior_cem)
    PRIOR=${CHECKPOINTS}/${BENCHMARK}_far_action_prior.pt
    ;;
  lewm_generator|generator_prior_top|sage)
    GENERATOR_ARGS=(--generator "${CHECKPOINTS}/${BENCHMARK}_generator.pt")
    ;;
esac
MANIFEST=${SAGE}/data/manifests/${BENCHMARK}/seed${SEED}/h${HORIZON}.json
OUT=${EVALUATION}/${BENCHMARK}/${METHOD}/seed${SEED}/h${HORIZON}
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache

cd "${SAGE}"
apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  PYTHONPATH="${SAGE}:${SNAPSHOT}:${SNAPSHOT}/lewm-runtime" \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" -m sage.eval.${BENCHMARK} \
    --method "${METHOD}" \
    --dataset "${DATASET}" \
    --policy "${LEWM}" \
    "${GENERATOR_ARGS[@]}" \
    --action-prior "${PRIOR}" \
    --manifest "${MANIFEST}" \
    --paper-config "${SAGE}/configs/paper.json" \
    --seed "${SEED}" \
    --device cuda:0 \
    --out-dir "${OUT}"

cd "${SNAPSHOT}"
"${ENV_DIR}/bin/python" "${SNAPSHOT}/validate_gdp_cem_e19_cell.py" \
  --result "${OUT}/results.json" \
  --benchmark "${BENCHMARK}" --method "${METHOD}" \
  --seed "${SEED}" --horizon "${HORIZON}" \
  --paper-config "${SAGE}/configs/paper.json" \
  --lewm "${LEWM}" --status "${OUT}/cell-status.json"
(cd "${OUT}" && sha256sum results.json cell-status.json > sha256.txt)
(cd "${OUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}/results.json" "${OUT}/cell-status.json" "${OUT}/sha256.txt" "${OUT}"
