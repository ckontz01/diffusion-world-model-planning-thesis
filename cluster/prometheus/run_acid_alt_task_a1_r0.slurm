#!/usr/bin/env bash

# Native A1 reproduction on the exact task R0 starts, one run per scorer seed.

#SBATCH --job-name=acid-alt-task-a1-r0
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=14:00:00
#SBATCH --array=0-2
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-a1-r0-%A_%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-a1-r0-%A_%a.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"; : "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"; : "${SCORER_JOB_ID:?submit with core scorer array ID}"; : "${PREFLIGHT_JOB_ID:?submit with successful task preflight job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"; IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"; CODE="${ROOT}/src/hi-lewm"; STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"; CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"; MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/r0-official-seed42.tsv"; PREFLIGHT="${ROOT}/results/acid-alternative/preflight/${TASK}/job-${PREFLIGHT_JOB_ID}/gate.json"; SEEDS=(6101 6102 6103); SEED="${SEEDS[${SLURM_ARRAY_TASK_ID}]}"; SCORER="${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-${SEED}-job-${SCORER_JOB_ID}-${SLURM_ARRAY_TASK_ID}/best.pt"
OUTPUT="${ROOT}/results/acid-alternative/r0/${TASK}/acid/train-seed-${SEED}-planner-seed-42-job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"; JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-a1-r0-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}"
for required in "${IMAGE}" "${SOURCE_MANIFEST}" "${DATASET}" "${CHECKPOINT}" "${MANIFEST}" "${SCORER}" "${PREFLIGHT}"; do test -f "${required}"; done
/usr/bin/python3 - "${PREFLIGHT}" "${TASK}" "$(sha256sum "${SOURCE_MANIFEST}" | cut -d' ' -f1)" <<'PYTHON'
import json, sys
gate=json.load(open(sys.argv[1], encoding="utf-8"))
if gate.get("status") != "pass" or gate.get("task") != sys.argv[2] or gate.get("source_manifest_sha256") != sys.argv[3]:
    raise SystemExit("A1 R0 is not authorized by the matching task preflight")
PYTHON
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"; trap 'rm -rf -- "${JOB_TMP}"' EXIT; export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"; nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" PYTHONHASHSEED=42 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg SLURM_JOB_ID="${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" \
  python -m acid_alternative.evaluate_matched --arm acid --code-root "${CODE}" --eval-config-name "${EVAL_CONFIG_NAME}" --stablewm-home "${STABLEWM_HOME}" --dataset "${DATASET}" --dataset-name "${DATASET_NAME}" --world-model-policy "${WORLD_MODEL_POLICY}" --world-model-checkpoint "${CHECKPOINT}" --source-manifest "${SOURCE_MANIFEST}" --scorer-checkpoint "${SCORER}" --eval-manifest "${MANIFEST}" --planner-seed 42 --lambda-weight 0.07 --goal-offset 25 --eval-budget 50 --horizon 5 --receding-horizon 5 --action-block 5 --cem-samples 300 --cem-steps 30 --cem-topk 30 --output-dir "${OUTPUT}"
printf '%s\n' "task=${TASK}" "training_seed=${SEED}" "planner_seed=42" "array_job_id=${SLURM_ARRAY_JOB_ID}" "array_task_id=${SLURM_ARRAY_TASK_ID}" "node=$(hostname)" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${PREFLIGHT}" "${OUTPUT}/summary.json" "${OUTPUT}/episodes.tsv" "${OUTPUT}/resolved-config.json" "${OUTPUT}/cem-diagnostics.jsonl" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
