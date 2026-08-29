#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-diag
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=12
#SBATCH --mem=96G
#SBATCH --gres=gpu:1
#SBATCH --time=24:00:00
#SBATCH --array=0-9%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-diag-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-diag-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable discrepancy snapshot}"
: "${RUN_ROOT:?missing unique discrepancy run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
SAGE=${SNAPSHOT}/official-sage
E19_SNAPSHOT=/lustreFS/data/superworld/ckontzias/thesis/snapshots/gdp-cem-e19-9f5499887c0d2e1f
E19_RUN=/lustreFS/data/superworld/ckontzias/thesis/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988
STABLEWM=${ROOT}/data/stablewm
CHECKPOINTS=${E19_RUN}/checkpoints
RUNS=${SNAPSHOT}/E19-DISCREPANCY-RUNS.tsv
JOB_TMP=/tmp/ckontzias-gdp-e19-diag-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sha256sum "${E19_SNAPSHOT}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = \
  9f5499887c0d2e1f9808cc5f493e7f172e717bcb8db202088e89e5c29f2a1d6c
(cd "${E19_SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "${E19_RUN}/preparation" && sha256sum -c sha256.txt >/dev/null)
(cd "${E19_RUN}/analysis" && sha256sum -c sha256.txt >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null

record=$(awk -F '\t' -v id="${SLURM_ARRAY_TASK_ID}" 'NR>1 && $1==id {print $0}' "${RUNS}")
test -n "${record}"
IFS=$'\t' read -r ARRAY_ID SENTINEL_ID REPEAT E19_ARRAY_ID BENCHMARK METHOD SEED HORIZON E19_RESULT_SHA <<< "${record}"
test "${ARRAY_ID}" = "${SLURM_ARRAY_TASK_ID}"
case "${METHOD}" in
  base_cem|far_goal_prior_cem|lewm_generator|generator_prior_top|sage) ;;
  *) exit 2 ;;
esac
test "${SEED}" = 32
case "${BENCHMARK}" in
  pusht)
    DATASET=${E19_RUN}/preparation/pusht_expert_train.lance
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

BASELINE=${E19_RUN}/evaluation/${BENCHMARK}/${METHOD}/seed${SEED}/h${HORIZON}/results.json
printf '%s  %s\n' "${E19_RESULT_SHA}" "${BASELINE}" | sha256sum --check --strict
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
OUT=${RUN_ROOT}/sentinels/s${SENTINEL_ID}/r${REPEAT}
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
  PYTHONPATH="${SNAPSHOT}/lewm-serialization-compat:${SAGE}:${SNAPSHOT}:${SNAPSHOT}/lewm-runtime" \
  MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg \
  TMPDIR="${JOB_TMP}" \
  E19_DISCREPANCY_SENTINEL_ID="${SENTINEL_ID}" \
  E19_DISCREPANCY_REPEAT="${REPEAT}" \
  E19_DISCREPANCY_TRACE="${OUT}/trace.json" \
  E19_DISCREPANCY_BANK="${OUT}/comparison-bank.pt" \
  "${ENV_DIR}/bin/python" -m trace_gdp_cem_e19_discrepancy \
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
(cd "${OUT}" && sha256sum \
  results.json cell-status.json trace.json comparison-bank.pt > sha256.txt)
(cd "${OUT}" && sha256sum -c sha256.txt >/dev/null)
chmod a-w "${OUT}/results.json" "${OUT}/cell-status.json" \
  "${OUT}/trace.json" "${OUT}/comparison-bank.pt" "${OUT}/sha256.txt" "${OUT}"
