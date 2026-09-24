#!/bin/bash
set -euo pipefail
[[ $# == 7 && -n ${SLURM_JOB_ID:-} && ${SLURM_CPUS_PER_TASK:-} == 4 ]] || exit 2
recovery="$1"
recovery_approval="$2"
package="$3"
approval="$4"
run="$5"
task="$6"
gpu="$7"
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
 ACVM_R1_APPROVAL="$recovery_approval" \
 SLURM_JOB_ID="$SLURM_JOB_ID" SLURM_CPUS_PER_TASK=4 SLURM_JOB_NODELIST="${SLURM_JOB_NODELIST:-}" CUDA_VISIBLE_DEVICES="$visible" \
 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl SDL_VIDEODRIVER=dummy \
 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4 \
 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
 "$runtime/bin/python" -B "$recovery/supervise.py" --approval "$approval" --run "$run" --task "$task"
