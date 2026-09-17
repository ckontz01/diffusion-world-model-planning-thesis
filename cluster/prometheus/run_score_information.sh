#!/usr/bin/env bash
# Future invocation only; this script never submits a job itself.
set -euo pipefail
[[ $# == 3 && -n ${SLURM_JOB_ID:-} && ${SLURM_CPUS_PER_TASK:-} == 4 ]] || exit 2
SRC=$(realpath "$1"); APPROVAL=$(realpath "$2"); OUT=$3
ROOT=/lustreFS/data/superworld/ckontzias/thesis
[[ "$OUT" == "$ROOT/experiments/candidate-value-score-information-20260918/"* && ! -e "$OUT" ]] || exit 2
(cd "$SRC" && sha256sum --check --quiet SI1-SOURCE-MANIFEST.sha256)
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
PARENT=$(dirname "$OUT")
[[ -d "$PARENT" ]] || exit 2
ulimit -f 1953125
apptainer exec --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$PARENT:$PARENT:rw" "$IMAGE" env \
 PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 SLURM_JOB_ID="$SLURM_JOB_ID" SLURM_CPUS_PER_TASK=4 CUDA_VISIBLE_DEVICES= \
 PYTHONPATH="$SRC/cluster/prometheus" OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 \
 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
 "$ENV/bin/python" -B "$SRC/cluster/prometheus/score_information.py" --approval "$APPROVAL" --output "$OUT"
