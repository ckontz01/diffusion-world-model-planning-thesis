#!/usr/bin/env bash

# Repeat the exact seed-42 B1 d=25 evaluation twice with determinism-related
# process environment variables set before Python imports PyTorch.

#SBATCH --job-name=hi-lewm-b1-det
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/b1-determinism-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/b1-determinism-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
COMPARATOR="${ROOT}/scripts/compare_episode_manifests.py"
OUTPUT="${STABLEWM_HOME}/repro/b1_determinism_d25_seed42_job_${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-b1-det-${SLURM_JOB_ID}"

if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing to overwrite existing diagnostic: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}" "${JOB_TMP}"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT

export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"
mkdir -p "${APPTAINER_TMPDIR}"

{
  echo "classification=b1_repeated_evaluation_determinism_diagnostic"
  echo "job_id=${SLURM_JOB_ID}"
  echo "node=$(hostname)"
  echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  sha256sum "${IMAGE}" "$0" "${COMPARATOR}"
  nvidia-smi --query-gpu=name,uuid,driver_version,memory.total --format=csv,noheader
} > "${OUTPUT}/provenance.txt"

run_repetition() {
  local repetition="$1"
  local repetition_dir="${OUTPUT}/rep${repetition}"
  local result_filename="b1_rep${repetition}_results.txt"
  mkdir -p "${repetition_dir}"
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
        planning.high.empirical_macro.enabled=true \
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
        +output.root_dir='"${repetition_dir}"'
    ' 2>&1 | tee "${repetition_dir}/console.log"
  test -s "${repetition_dir}/${result_filename}"
  test -s "${repetition_dir}/b1_rep${repetition}_results_episodes.tsv"
}

echo "job_id=${SLURM_JOB_ID}"
echo "node=$(hostname)"
nvidia-smi
run_repetition 1
run_repetition 2

python3.9 "${COMPARATOR}" \
  "${OUTPUT}/rep1/b1_rep1_results_episodes.tsv" \
  "${OUTPUT}/rep2/b1_rep2_results_episodes.tsv" \
  --first-label rep1 \
  --second-label rep2 \
  --output-json "${OUTPUT}/comparison.json"

find "${OUTPUT}" -type f ! -name checksums.sha256 -print0 \
  | sort -z \
  | xargs -0 sha256sum > "${OUTPUT}/checksums.sha256"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "${OUTPUT}/provenance.txt"
