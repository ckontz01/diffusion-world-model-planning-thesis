#!/usr/bin/env bash

# Single-environment end-to-end episode wall-clock latency for all five arms.

#SBATCH --job-name=acid-alt-task-lat-episode
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=10:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-lat-episode-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-lat-episode-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"; : "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"; : "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"; : "${CORE_SCORER_JOB_ID:?submit with core scorer array ID}"; : "${REACHABILITY_JOB_ID:?submit with reachability array ID}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"; CODE="${ROOT}/src/hi-lewm"; STABLEWM_HOME="${ROOT}/data/stablewm"; SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
DATASET="${STABLEWM_HOME}/${DATASET_RELATIVE_PATH}"; CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"; MANIFEST="${ROOT}/manifests/acid-alternative-v1/${TASK}/d1-fresh-development.tsv"; ACID="${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-6101-job-${CORE_SCORER_JOB_ID}-0/best.pt"; REACHABILITY="${ROOT}/results/acid-alternative/scorers/${TASK}/reachability/true/seed-6101-job-${REACHABILITY_JOB_ID}-0/best.pt"; DIFFUSION="${ROOT}/results/acid-alternative/scorers/${TASK}/diffusion/true/seed-6101-job-${CORE_SCORER_JOB_ID}-3/best.pt"; FORWARD="${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-6101-job-${CORE_SCORER_JOB_ID}-6/best.pt"; OUTPUT="${ROOT}/results/acid-alternative/latency/${TASK}/end-to-end-episode/job-${SLURM_JOB_ID}"; JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-lat-episode-${SLURM_JOB_ID}"
for required in "${SOURCE_MANIFEST}" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${IMAGE}" "${DATASET}" "${CHECKPOINT}" "${MANIFEST}" "${ACID}" "${REACHABILITY}" "${DIFFUSION}" "${FORWARD}"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi; mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"; trap 'rm -rf -- "${JOB_TMP}"' EXIT; export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"; nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" --bind "/usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro" "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy MPLBACKEND=Agg SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" python -m acid_alternative_diagnostics.benchmark_episode_latency --code-root "${CODE}" --eval-config-name "${EVAL_CONFIG_NAME}" --stablewm-home "${STABLEWM_HOME}" --dataset "${DATASET}" --dataset-name "${DATASET_NAME}" --world-model-policy "${WORLD_MODEL_POLICY}" --world-model-checkpoint "${CHECKPOINT}" --source-manifest "${SOURCE_MANIFEST}" --eval-manifest "${MANIFEST}" --planner-seed 7101 --lambda-weight 0.07 --goal-offset 25 --eval-budget 50 --horizon 5 --receding-horizon 5 --action-block 5 --cem-samples 300 --cem-steps 30 --cem-topk 30 --diffusion-sigma 0.10 --diffusion-sigma 0.25 --diffusion-sigma 0.50 --scorer "acid=acid=${ACID}" --scorer "reachability=reachability=${REACHABILITY}" --scorer "diffusion=diffusion=${DIFFUSION}" --scorer "forward=forward=${FORWARD}" --warmup-episodes 1 --measured-episodes 5 --output-dir "${OUTPUT}"
printf '%s\n' "task=${TASK}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"; sha256sum "$0" "${SOURCE_MANIFEST}" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${OUTPUT}/summary.json" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
