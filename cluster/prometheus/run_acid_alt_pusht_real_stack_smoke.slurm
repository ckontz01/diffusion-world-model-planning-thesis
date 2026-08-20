#!/usr/bin/env bash

#SBATCH --job-name=acid-alt-pusht-smoke
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-smoke-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-alt-pusht-smoke-%j.err

set -euo pipefail

ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
TOOLS_DIR="${ROOT}/envs/hi-lewm-tools"
CODE="${ROOT}/src/hi-lewm"
STABLEWM_HOME="${ROOT}/data/stablewm"
DATASET="${STABLEWM_HOME}/pusht_expert_train.h5"
PARTITIONS="${ROOT}/manifests/partitions/pusht-v1/episodes-seed-20260728.tsv"
ROLES="${ROOT}/manifests/partitions/pusht-v1/p1-train-val-seed-20260728.tsv"
CHECKPOINT="${STABLEWM_HOME}/pusht/lewm_hf_22b330c_object.ckpt"
OUTPUT="${ROOT}/results/acid-alternative/preflight/pusht-real-stack-job-${SLURM_JOB_ID}"
JOB_TMP="/tmp/ckontzias-acid-alt-smoke-${SLURM_JOB_ID}"

for required in "${IMAGE}" "${DATASET}" "${PARTITIONS}" "${ROLES}" "${CHECKPOINT}"; do
  test -f "${required}"
done
if [[ -e "${OUTPUT}" ]]; then
  echo "Refusing existing output: ${OUTPUT}" >&2
  exit 2
fi
mkdir -p "${OUTPUT}" "${JOB_TMP}/apptainer"
cleanup() {
  rm -rf -- "${JOB_TMP}"
}
trap cleanup EXIT
export APPTAINER_TMPDIR="${JOB_TMP}/apptainer"
export APPTAINER_CACHEDIR="${ROOT}/tmp/apptainer-cache"

echo "job_id=${SLURM_JOB_ID}"
echo "node=$(hostname)"
echo "start_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
nvidia-smi

apptainer exec --nv --cleanenv \
  --bind "${ROOT}:${ROOT}" \
  --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -euo pipefail
    export PATH="'"${TOOLS_DIR}"'/bin:'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export PYTHONPATH="'"${ROOT}"'/scripts:'"${CODE}"':'"${CODE}"'/third_party/lewm"
    export STABLEWM_HOME="'"${STABLEWM_HOME}"'"
    export TMPDIR="'"${JOB_TMP}"'"
    export MPLBACKEND=Agg
    export MUJOCO_GL=egl
    export SDL_VIDEODRIVER=dummy

    python -m acid_alternative.real_stack_smoke \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --policy pusht/lewm_hf_22b330c \
      --checkpoint-file "'"${CHECKPOINT}"'" \
      --dataset "'"${DATASET}"'" \
      --action-dim 10 \
      --output-json "'"${OUTPUT}"'/wrapper-smoke.json"

    python -m acid_alternative.extract_flat_latents \
      --stablewm-home "'"${STABLEWM_HOME}"'" \
      --dataset "'"${DATASET}"'" \
      --partition-manifest "'"${PARTITIONS}"'" \
      --partition P1 \
      --policy pusht/lewm_hf_22b330c \
      --checkpoint-file "'"${CHECKPOINT}"'" \
      --episode-limit 2 \
      --batch-size 128 \
      --output-h5 "'"${OUTPUT}"'/latents.h5" \
      --output-json "'"${OUTPUT}"'/latents.json"

    python -m acid_alternative.build_transition_cache \
      --dataset "'"${DATASET}"'" \
      --latent-h5 "'"${OUTPUT}"'/latents.h5" \
      --latent-manifest "'"${OUTPUT}"'/latents.json" \
      --p1-role-manifest "'"${ROLES}"'" \
      --frameskip 5 \
      --episode-limit 2 \
      --output-h5 "'"${OUTPUT}"'/transitions.h5" \
      --output-json "'"${OUTPUT}"'/transitions.json"

    for model in acid diffusion forward; do
      python -m acid_alternative.train_transition_scorer \
        --model "${model}" \
        --condition true \
        --latent-h5 "'"${OUTPUT}"'/latents.h5" \
        --latent-manifest "'"${OUTPUT}"'/latents.json" \
        --transition-h5 "'"${OUTPUT}"'/transitions.h5" \
        --transition-manifest "'"${OUTPUT}"'/transitions.json" \
        --output-dir "'"${OUTPUT}"'/train-${model}" \
        --seed 6101 \
        --maximum-steps 50 \
        --warmup-steps 10 \
        --batch-size 32 \
        --validation-batch-size 128 \
        --validation-interval 25 \
        --validation-limit 128
    done
  '

sha256sum "${OUTPUT}"/*.json "${OUTPUT}"/train-*/*.json "${OUTPUT}"/train-*/best.pt > "${OUTPUT}/sha256.txt"
echo "finish_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
