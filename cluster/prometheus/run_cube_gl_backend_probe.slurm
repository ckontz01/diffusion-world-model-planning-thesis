#!/usr/bin/env bash

#SBATCH --job-name=cube-gl-probe
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/cube-gl-probe-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/cube-gl-probe-%j.err

set -euo pipefail
ROOT="/lustreFS/data/superworld/ckontzias/thesis"
IMAGE="${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif"
ENV_DIR="${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006"
JOB_TMP="/tmp/ckontzias-cube-gl-probe-${SLURM_JOB_ID}"
mkdir -p "${JOB_TMP}"
cleanup() { rm -rf -- "${JOB_TMP}"; }
trap cleanup EXIT

apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  "${IMAGE}" /bin/bash -c '
    set -u
    export PATH="'"${ENV_DIR}"'/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export PYTHONNOUSERSITE=1
    export TMPDIR="'"${JOB_TMP}"'"
    echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
    nvidia-smi --query-gpu=name,uuid,driver_version --format=csv,noheader
    ldconfig -p 2>/dev/null | grep -E "EGL|OSMesa|GLX" || true
    find /usr/share/glvnd /etc/glvnd -maxdepth 4 \( -type f -o -type l \) -print 2>/dev/null || true
    for backend in egl osmesa glfw; do
      echo "backend=${backend}"
      if [[ "${backend}" == egl ]]; then
        env MUJOCO_GL=egl PYOPENGL_PLATFORM=egl python -c \
          "import os; from dm_control import mjcf; print(\"import_ok\", os.environ.get(\"MUJOCO_GL\"))"
      elif [[ "${backend}" == osmesa ]]; then
        env MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa python -c \
          "import os; from dm_control import mjcf; print(\"import_ok\", os.environ.get(\"MUJOCO_GL\"))"
      else
        env -u PYOPENGL_PLATFORM MUJOCO_GL=glfw python -c \
          "import os; from dm_control import mjcf; print(\"import_ok\", os.environ.get(\"MUJOCO_GL\"))"
      fi
      echo "backend_exit=$?"
    done
    exit 0
  '
