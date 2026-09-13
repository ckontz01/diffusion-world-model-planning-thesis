#!/usr/bin/env bash
# Explicit invocation only: no submission, monitor, training, or GPU request.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "Usage: bash $0 {summary|outcomes|traces} NEW_OUTPUT_DIRECTORY" >&2
  exit 2
fi
MODE=$1
OUT=$(realpath -m -- "$2")
SRC=$(cd -- "$(dirname -- "$0")" && pwd)
ROOT=/lustreFS/data/superworld/ckontzias/thesis
STUDY=$ROOT/experiments/independent-pusht/final-20260906-4a608e5
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
case "$OUT/" in "$STUDY/"*) echo 'Output must be outside historical study' >&2; exit 2;; esac
case "$MODE" in
  summary) SCRIPT=diffusion_bottleneck.py; ARGS=(--summary "$STUDY/analysis-0/SUMMARY.json");;
  outcomes) SCRIPT=diffusion_bottleneck.py; ARGS=(--archive "$STUDY/analysis-0");;
  traces) SCRIPT=diffusion_bottleneck_traces.py; ARGS=(--study "$STUDY");;
  *) echo 'Unknown mode' >&2; exit 2;;
esac
[[ -f "$IMAGE" && -x "$ENV/bin/python" && -f "$SRC/$SCRIPT" ]] || { echo 'Pinned runtime or source missing' >&2; exit 2; }
[[ ! -e "$OUT" ]] || { echo 'Refusing to reuse output directory' >&2; exit 2; }
mkdir -p -- "$(dirname -- "$OUT")"
mkdir -m 700 -- "$OUT"
# Source/artifacts are read-only; only this new report directory is writable.
apptainer exec --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$SRC:$SRC:ro" --bind "$OUT:$OUT:rw" \
  "$IMAGE" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$ENV/bin/python" "$SRC/$SCRIPT" "${ARGS[@]}" --out "$OUT/REPORT.json"
sha256sum -- "$OUT/REPORT.json" > "$OUT/REPORT.sha256"
