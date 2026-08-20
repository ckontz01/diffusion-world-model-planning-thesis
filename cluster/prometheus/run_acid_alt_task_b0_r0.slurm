#!/usr/bin/env bash

# Released Le-WM original-CEM R0 reproduction for one task.

#SBATCH --job-name=acid-alt-task-b0-r0
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-b0-r0-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-b0-r0-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${PREFLIGHT_JOB_ID:?submit with successful task preflight job ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"; CODE="${ROOT}/src/hi-lewm"; STABLEWM_HOME="${ROOT}/data/stablewm"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"; CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"; MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/r0-official-seed42.tsv"
PREFLIGHT="${ROOT}/results/acid-alternative/preflight/${TASK}/job-${PREFLIGHT_JOB_ID}/gate.json"
OUTPUT="${ROOT}/results/acid-alternative/r0/${TASK}/b0/planner-seed-42-job-${SLURM_JOB_ID}"; JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-b0-r0-${SLURM_JOB_ID}"
for required in "${IMAGE}" "${SOURCE_MANIFEST}" "${DATASET}" "${CHECKPOINT}" "${MANIFEST}" "${PREFLIGHT}"; do test -f "${required}"; done
/usr/bin/python3 - "${PREFLIGHT}" "${TASK}" "$(sha256sum "${SOURCE_MANIFEST}" | cut -d' ' -f1)" <<'PYTHON'
import json, sys
gate=json.load(open(sys.argv[1], encoding="utf-8"))
if gate.get("status") != "pass" or gate.get("task") != sys.argv[2] or gate.get("source_manifest_sha256") != sys.argv[3]:
    raise SystemExit("R0 is not authorized by the matching task preflight")
PYTHON
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"; trap 'rm -rf -- "${JOB_TMP}"' EXIT; export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"; nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" PYTHONHASHSEED=42 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  python -m acid_alternative.evaluate_matched --arm b0 --code-root "${CODE}" --eval-config-name "${EVAL_CONFIG_NAME}" --stablewm-home "${STABLEWM_HOME}" --dataset "${DATASET}" --dataset-name "${DATASET_NAME}" --world-model-policy "${WORLD_MODEL_POLICY}" --world-model-checkpoint "${CHECKPOINT}" --source-manifest "${SOURCE_MANIFEST}" --eval-manifest "${MANIFEST}" --planner-seed 42 --lambda-weight 0.07 --goal-offset 25 --eval-budget 50 --horizon 5 --receding-horizon 5 --action-block 5 --cem-samples 300 --cem-steps 30 --cem-topk 30 --output-dir "${OUTPUT}"
/usr/bin/python3 - "${OUTPUT}/summary.json" "${PUBLISHED_LEWM_B0}" <<'PYTHON'
import json, math, sys
summary=json.load(open(sys.argv[1], encoding="utf-8")); rate=summary.get("success_rate_fraction"); published=float(sys.argv[2])
if not isinstance(rate,(int,float)) or not math.isfinite(rate): raise SystemExit("non-finite B0 rate")
if abs(rate-published)>0.10+1e-12: raise SystemExit(f"B0 reproduction gate failed: observed={rate:.6f}, published={published:.6f}")
PYTHON
printf '%s\n' "task=${TASK}" "published_lewm_b0=${PUBLISHED_LEWM_B0}" "job_id=${SLURM_JOB_ID}" "node=$(hostname)" > "${OUTPUT}/provenance.txt"
sha256sum "$0" "${SOURCE_MANIFEST}" "${PREFLIGHT}" "${OUTPUT}/summary.json" "${OUTPUT}/episodes.tsv" "${OUTPUT}/resolved-config.json" "${OUTPUT}/cem-diagnostics.jsonl" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
