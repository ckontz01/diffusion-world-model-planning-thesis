#!/bin/bash
set -euo pipefail
[[ $# == 5 && -n ${SLURM_JOB_ID:-} && ${SLURM_CPUS_PER_TASK:-} == 4 ]] || exit 2
package="$1"
approval="$2"
run="$3"
task="$4"
gpu="$5"
root=/lustreFS/data/superworld/ckontzias/thesis
image=/lustreFS/data/superworld/ckontzias/thesis/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
runtime=/lustreFS/data/superworld/ckontzias/thesis/envs/hi-lewm-artifact-py311-cu121-swm006
flags=()
visible=${CUDA_VISIBLE_DEVICES:-}
if [[ "$gpu" == 1 ]]; then flags+=(--nv); [[ -n "$visible" ]] || exit 2; else visible=; fi
[[ $(sha256sum "$image" | cut -d' ' -f1) == 589af9b428527ae2d315fbd5eaf7ef991efb1aa7249e30a6d28e6731df40afb2 ]] || exit 2
exec apptainer exec --cleanenv "${flags[@]}" --bind "$root:$root:ro" --bind "$run:$run:rw" "$image" env \
 PATH="$runtime/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 SLURM_JOB_ID="$SLURM_JOB_ID" SLURM_CPUS_PER_TASK=4 CUDA_VISIBLE_DEVICES="$visible" \
 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl SDL_VIDEODRIVER=dummy \
 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4 \
 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
 "$runtime/bin/python" -B "$package/supervise.py" --approval "$approval" --run "$run" --task "$task"
