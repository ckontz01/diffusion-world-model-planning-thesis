#!/usr/bin/env bash
# Launch plumbing only: executes the already-frozen verifier without edits.
set -euo pipefail
[[ -n ${SLURM_JOB_ID:-} ]] || exit 2
ROOT=/lustreFS/data/superworld/ckontzias/thesis
SRC=$ROOT/snapshots/single-anchor-ranking-20260914-ba2eb02b2e860648
RUN=$ROOT/experiments/single-anchor-ranking-20260914/run-ba2eb02b
SOURCE_SHA=ba2eb02b2e860648a0642c39cb97f3409ab9cb7dcc975a4110b5e2db05297704
PROTOCOL_SHA=43830bd18fcf8cf3d986cbd71d5bb8d5df0dee8fd7c88356c5070b5d76c8a1ae
[[ $(sha256sum "$SRC/SOURCE-MANIFEST.sha256" | cut -d' ' -f1) == "$SOURCE_SHA" ]] || exit 2
(cd "$SRC" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
[[ -f "$RUN/DISPATCH-COMPLETE.json" && ! -e "$RUN/analysis" ]] || exit 2
mkdir "$RUN/verify-tmp"
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ulimit -f 65536
apptainer exec --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN:$RUN:rw" "$IMAGE" env \
 PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 PYTHONPATH="$SRC/cluster/prometheus" CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 \
 TMPDIR="$RUN/verify-tmp" "$ENV/bin/python" "$SRC/cluster/prometheus/verify_single_anchor_ranking.py" \
 --root "$RUN" --src "$SRC" --source-sha "$SOURCE_SHA" \
 --protocol "$SRC/docs/single-anchor-ranking-20260914/PROTOCOL.md" --protocol-sha "$PROTOCOL_SHA" \
 --combined "$SRC/docs/bottleneck/receipts/EXTENSION-COMBINED-301071.json" \
 --completion "$RUN/DISPATCH-COMPLETE.json" --out "$RUN/analysis"
