#!/usr/bin/env bash

# CUDA-event cost-component and full-CEM latency for all five headline arms.

#SBATCH --job-name=acid-alt-task-lat-cuda
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=05:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-lat-cuda-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-task-lat-cuda-%j.err

set -euo pipefail
: "${TASK:?submit with TASK=pusht|reacher|cube}"
: "${CORE_SNAPSHOT:?submit with immutable core snapshot path}"
: "${DIAG_SNAPSHOT:?submit with immutable diagnostic snapshot path}"
: "${CAPTURE_JOB_ID:?submit with candidate capture job ID}"
: "${CORE_SCORER_JOB_ID:?submit with core scorer array ID}"
: "${REACHABILITY_JOB_ID:?submit with reachability array ID}"
: "${DIFFUSION_MODE:=multi}"
ROOT="/lustreFS/data/superworld/ckontzias/thesis"; IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"; ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"; TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"; CODE="${ROOT}/src/hi-lewm"; STABLEWM_HOME="${ROOT}/data/stablewm"; SOURCE_MANIFEST="${CORE_SNAPSHOT}/SOURCE-MANIFEST.sha256"
eval "$(apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env PYTHONPATH="${CORE_SNAPSHOT}" "${ENV_DIR}/bin/python" -m acid_alternative.print_task_spec "${TASK}" --format shell)"
CHECKPOINT="${STABLEWM_HOME}/${CHECKPOINT_RELATIVE_PATH}"; CAPTURE="${ROOT}/results/acid-alternative/diagnostics/${TASK}/d1-b0-candidate-pools/planner-seed-7101-job-${CAPTURE_JOB_ID}"; ACID="${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-6101-job-${CORE_SCORER_JOB_ID}-0/best.pt"; REACHABILITY="${ROOT}/results/acid-alternative/scorers/${TASK}/reachability/true/seed-6101-job-${REACHABILITY_JOB_ID}-0/best.pt"; DIFFUSION="${ROOT}/results/acid-alternative/scorers/${TASK}/diffusion/true/seed-6101-job-${CORE_SCORER_JOB_ID}-3/best.pt"; FORWARD="${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-6101-job-${CORE_SCORER_JOB_ID}-6/best.pt"; JOB_TMP="/tmp/ckontzias-acid-alt-${TASK}-lat-cuda-${SLURM_JOB_ID}"
case "${DIFFUSION_MODE}" in multi) sigma_arguments=(--diffusion-sigma 0.10 --diffusion-sigma 0.25 --diffusion-sigma 0.50) ;; sigma010) sigma_arguments=(--diffusion-sigma 0.10) ;; sigma025) sigma_arguments=(--diffusion-sigma 0.25) ;; sigma050) sigma_arguments=(--diffusion-sigma 0.50) ;; *) echo "invalid DIFFUSION_MODE" >&2; exit 2 ;; esac
OUTPUT="${ROOT}/results/acid-alternative/latency/${TASK}/cuda-components/${DIFFUSION_MODE}/job-${SLURM_JOB_ID}"
for required in "${SOURCE_MANIFEST}" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${IMAGE}" "${CHECKPOINT}" "${CAPTURE}/candidate-pools.pt" "${CAPTURE}/manifest.json" "${ACID}" "${REACHABILITY}" "${DIFFUSION}" "${FORWARD}"; do test -f "${required}"; done
if [[ -e "${OUTPUT}" ]]; then echo "Refusing existing output" >&2; exit 2; fi; mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"; trap 'rm -rf -- "${JOB_TMP}"' EXIT; export APPTAINER_TMPDIR="${JOB_TMP}/apptainer" APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"; nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${DIAG_SNAPSHOT}:${CORE_SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" python -m acid_alternative_diagnostics.benchmark_latency --candidate-artifact "${CAPTURE}/candidate-pools.pt" --candidate-manifest "${CAPTURE}/manifest.json" --stablewm-home "${STABLEWM_HOME}" --world-model-policy "${WORLD_MODEL_POLICY}" --world-model-checkpoint "${CHECKPOINT}" --source-manifest "${SOURCE_MANIFEST}" --lambda-weight 0.07 "${sigma_arguments[@]}" --scorer "acid=acid=${ACID}" --scorer "reachability=reachability=${REACHABILITY}" --scorer "diffusion=diffusion=${DIFFUSION}" --scorer "forward=forward=${FORWARD}" --pool-index 0 --warmup-calls 20 --measured-calls 100 --full-solve-warmups 1 --full-solve-repetitions 10 --cem-samples 300 --cem-steps 30 --cem-topk 30 --planner-seed 7101 --output-dir "${OUTPUT}"
printf '%s\n' "task=${TASK}" "diffusion_mode=${DIFFUSION_MODE}" "job_id=${SLURM_JOB_ID}" > "${OUTPUT}/provenance.txt"; sha256sum "$0" "${SOURCE_MANIFEST}" "${DIAG_SNAPSHOT}/SOURCE-MANIFEST.sha256" "${OUTPUT}/summary.json" "${OUTPUT}/provenance.txt" > "${OUTPUT}/sha256.txt"
