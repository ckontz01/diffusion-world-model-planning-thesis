#!/usr/bin/env bash
set -euo pipefail
[[ $# == 4 && -n ${SLURM_JOB_ID:-} && ${SLURM_CPUS_PER_TASK:-} == 4 ]] || exit 2
SRC=$(realpath "$1"); APPROVAL=$(realpath "$2"); RUN=$(realpath "$3"); TASK=$4
ROOT=/lustreFS/data/superworld/ckontzias/thesis
[[ "$RUN" == "$ROOT/experiments/local-goal-search-budget-20260919/"* && ! -e "$RUN/$TASK" ]] || exit 2
(cd "$SRC" && sha256sum --check --quiet LGP-RB1-SOURCE-MANIFEST.sha256)
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
[[ $(sha256sum "$IMAGE" | cut -d' ' -f1) == 589af9b428527ae2d315fbd5eaf7ef991efb1aa7249e30a6d28e6731df40afb2 ]] || exit 2
GPU_ARGS=(--nv); VISIBLE=${CUDA_VISIBLE_DEVICES:-}
if [[ "$TASK" == analysis ]]; then GPU_ARGS=(); VISIBLE=; else [[ -n "$VISIBLE" ]] || exit 2; fi
ulimit -f 3906250
apptainer exec --cleanenv "${GPU_ARGS[@]}" --bind "$ROOT:$ROOT:ro" --bind "$RUN:$RUN:rw" "$IMAGE" env \
 PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 SLURM_JOB_ID="$SLURM_JOB_ID" SLURM_CPUS_PER_TASK=4 CUDA_VISIBLE_DEVICES="$VISIBLE" \
 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl SDL_VIDEODRIVER=dummy \
 PYTHONPATH="$SRC/cluster/prometheus" OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
 "$ENV/bin/python" -B "$SRC/cluster/prometheus/lgprb1_worker.py" --source "$SRC" --approval "$APPROVAL" --run "$RUN" --task "$TASK"
