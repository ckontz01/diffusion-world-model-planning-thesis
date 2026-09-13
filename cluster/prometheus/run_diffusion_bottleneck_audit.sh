#!/usr/bin/env bash
# Explicit Slurm allocation only. Immutable historical tree is mounted read-only.
set -euo pipefail
[[ -n ${SLURM_JOB_ID:-} && $# == 2 ]] || { echo 'Requires allocation, source root, new output'; exit 2; }
SRC=$(realpath "$1")
OUT=$(realpath -m "$2")
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STUDY=$ROOT/experiments/independent-pusht/final-20260906-4a608e5
[[ "$OUT" == "$ROOT/experiments/diffusion-bottleneck/"* && ! -e "$OUT" ]]
(cd "$SRC" && sha256sum -c SOURCE-MANIFEST.sha256)
mkdir -m 700 "$OUT"
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
apptainer exec --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$OUT:$OUT:rw" "$IMAGE" \
 env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 PYTHONPATH="$SRC/cluster/prometheus" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
 "$ENV/bin/python" "$SRC/cluster/prometheus/execute_diffusion_bottleneck_audit.py" "$SRC" "$OUT" "$STUDY"
sha256sum "$OUT"/*.json "$OUT"/*.txt > "$OUT/sha256.txt"
