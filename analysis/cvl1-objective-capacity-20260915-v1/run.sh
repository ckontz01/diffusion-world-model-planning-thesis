#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 && -n ${SLURM_JOB_ID:-} ]] || exit 2
SRC=$(realpath "$1")
OUT=$(realpath "$2")
ROOT=/lustreFS/data/superworld/ckontzias/thesis
[[ "$OUT" == "$ROOT/experiments/cvl1-objective-capacity-20260915-v1/"* ]] || exit 2
(cd "$SRC" && sha256sum --check --quiet SOURCE.sha256)
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ulimit -f 131072
apptainer exec --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$OUT:$OUT:rw" "$IMAGE" env \
 PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= \
 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
 SLURM_JOB_ID="$SLURM_JOB_ID" \
 "$ENV/bin/python" "$SRC/study.py" --out "$OUT/results"
