#!/usr/bin/env bash

# One-seed development pilot for the published Hi-LeWM B0/B1 comparison.
# This is deliberately not labelled as a three-seed paper reproduction because
# the released artifact specifies only seed 42 even though the paper reports
# means across three seeds.

#SBATCH --job-name=hi-lewm-b0-b1-d25
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-b0-b1-d25-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/pusht-b0-b1-d25-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
RUNNER="${ROOT}/scripts/run_pusht_b0_b1_d25_pilot.slurm"
VALIDATOR="${ROOT}/scripts/validate_pusht_b0_b1_pilot_v2.py"
PILOT_ID="pusht_b0_b1_d25_seed42_job_${SLURM_JOB_ID}"
OUTPUT_BASE="${STABLEWM_HOME}/repro/${PILOT_ID}"
JOB_TMP="/tmp/ckontzias-hi-lewm-b0-b1-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${RUNNER}" "${VALIDATOR}"; do
  if [[ ! -f "${required}" ]]; then
    echo "Missing required file: ${required}" >&2
    exit 2
  fi
done
if [[ -e "${OUTPUT_BASE}" ]]; then
  echo "Refusing to overwrite existing pilot output: ${OUTPUT_BASE}" >&2
  exit 2
fi
if [[ "${JOB_TMP}" != "/tmp/ckontzias-hi-lewm-b0-b1-${SLURM_JOB_ID}" ]]; then
  echo "Unexpected job scratch path: ${JOB_TMP}" >&2
  exit 2
fi

mkdir -p "${OUTPUT_BASE}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "pilot_id=${PILOT_ID}"
  echo "classification=development_pilot_not_paper_reproduction"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "artifact_seed=42"
  echo "goal_offset_steps=25"
  echo "eval_budget=50"
  echo "num_eval=50"
  sha256sum "${IMAGE}" "${RUNNER}" "${VALIDATOR}"
  sha256sum "${STABLEWM_HOME}/runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15_object.ckpt"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT_BASE}/provenance.txt"

echo "pilot_id=${PILOT_ID}"
echo "output_base=${OUTPUT_BASE}"
echo "node=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
nvidia-smi

run_arm() {
  local arm="$1"
  local empirical_enabled="$2"
  local arm_dir="${OUTPUT_BASE}/${arm}"
  local result_filename="${arm}_results.txt"
  mkdir -p "${arm_dir}"

  echo "arm=${arm}"
  echo "empirical_macro_enabled=${empirical_enabled}"
  echo "arm_start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  apptainer exec --nv --cleanenv \
    --bind "${ROOT}:${ROOT}" \
    --bind "${JOB_TMP}:${JOB_TMP}" \
    "${IMAGE}" /bin/bash -c '
      set -euo pipefail
      export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export PYTHONHASHSEED=42
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    export EVAL_DETERMINISM=strict
    export TMPDIR="'"${JOB_TMP}"'"
      export MPLBACKEND=Agg
      export MUJOCO_GL=egl
      export SDL_VIDEODRIVER=dummy
      export HYDRA_FULL_ERROR=1
      cd "'"${CODE}"'"
      python - <<"PY"
import importlib.metadata as metadata
import torch

print(f"python_torch={torch.__version__}")
print(f"torch_cuda={torch.version.cuda}")
print(f"cuda_available={torch.cuda.is_available()}")
print(f"gpu={torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}")
print(f"stable_worldmodel={metadata.version('"'"'stable-worldmodel'"'"')}")
assert torch.cuda.is_available(), "CUDA is not available inside Apptainer"
assert metadata.version("stable-worldmodel") == "0.0.6"
PY
      python -m h_le_wm.eval.hierarchical \
        --config-name=hi_pusht \
        policy=runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \
        seed=42 \
        planning.mode=hierarchical \
        eval.num_eval=50 \
        eval.goal_offset_steps=25 \
        eval.eval_budget=50 \
        planning.high.solver.device=cuda \
        planning.high.solver.batch_size=1 \
        planning.high.solver.num_samples=900 \
        planning.high.solver.var_scale=1.0 \
        planning.high.solver.n_steps=20 \
        planning.high.solver.topk=10 \
        planning.high.plan_config.horizon=1 \
        planning.high.plan_config.receding_horizon=1 \
        planning.high.plan_config.action_block=1 \
        planning.high.replan_interval=5 \
        planning.high.latent_prior.enabled=true \
        planning.high.latent_prior.num_chunks=2048 \
        planning.high.latent_prior.min_chunks_for_stats=64 \
        planning.high.latent_prior.chunk_len=5 \
        planning.high.latent_prior.lower_q=5.0 \
        planning.high.latent_prior.upper_q=95.0 \
        planning.high.latent_prior.margin_ratio=0.05 \
        planning.high.latent_prior.clamp_abs=3.0 \
        planning.high.latent_prior.fallback_abs=1.0 \
        planning.high.empirical_macro.enabled='"${empirical_enabled}"' \
        planning.high.empirical_macro.num_sequences=4096 \
        planning.high.empirical_macro.chunk_len=5 \
        planning.high.empirical_macro.residual_scale=0.1 \
        planning.high.empirical_macro.min_residual_std=0.001 \
        planning.high.empirical_macro.return_top_candidates=8 \
        planning.high.empirical_macro.encode_batch_size=4096 \
        planning.high.empirical_macro.stage_sampling=sequence \
        planning.high.empirical_macro.seed=42 \
        planning.low.solver.device=cuda \
        planning.low.solver.batch_size=1 \
        planning.low.solver.num_samples=300 \
        planning.low.solver.var_scale=1.0 \
        planning.low.solver.n_steps=30 \
        planning.low.solver.topk=150 \
        planning.low.plan_config.horizon=2 \
        planning.low.plan_config.receding_horizon=1 \
        planning.low.plan_config.action_block=5 \
        solver.device=cuda \
        output.subdir=. \
        output.filename='"${result_filename}"' \
        +output.root_dir='"${arm_dir}"'
    ' 2>&1 | tee "${arm_dir}/console.log"

  test -s "${arm_dir}/${result_filename}"
  test -s "${arm_dir}/${arm}_results_episodes.tsv"
  echo "arm_finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

run_arm b0 false
run_arm b1 true

apptainer exec --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    python "'"${VALIDATOR}"'" "'"${OUTPUT_BASE}"'" --expected-episodes 50
  ' | tee "${OUTPUT_BASE}/validation.json"

find "${OUTPUT_BASE}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT_BASE}/checksums.sha256"

echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "${OUTPUT_BASE}/provenance.txt"
echo "B0/B1 PushT d=25 development pilot completed and validated."
