#!/usr/bin/env bash
set -euo pipefail
[[ $# == 7 && -n ${SLURM_JOB_ID:-} ]] || exit 2
SRC=$(realpath "$1"); RUN=$(realpath "$2"); APPROVAL=$(realpath "$3")
CAPSULE=$(realpath "$4"); SOURCE_SHA=$5; KIND=$6; INDEX=$7
ROOT=/lustreFS/data/superworld/ckontzias/thesis
[[ "$RUN" == "$ROOT/experiments/candidate-value-learning-20260914/run-"* ]] || exit 2
[[ "$KIND" =~ ^(preflight|train|validation|fit|validate|closed|report)$ && "$INDEX" =~ ^[0-9]+$ ]] || exit 2
[[ $(sha256sum "$SRC/SOURCE-MANIFEST.sha256" | cut -d' ' -f1) == "$SOURCE_SHA" ]] || exit 2
(cd "$SRC" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
mkdir "$RUN/tmp-$KIND-$INDEX"
NV=()
case "$KIND" in preflight|train|validation|closed) NV=(--nv);; esac
ulimit -f 1048576
apptainer exec "${NV[@]}" --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN:$RUN:rw" "$IMAGE" env \
 PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 SLURM_JOB_ID="$SLURM_JOB_ID" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
 PYTHONPATH="$SRC/cluster/prometheus:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm" \
 SDL_VIDEODRIVER=dummy CUBLAS_WORKSPACE_CONFIG=:4096:8 MPLBACKEND=Agg \
 MPLCONFIGDIR="$RUN/tmp-$KIND-$INDEX/mpl" TMPDIR="$RUN/tmp-$KIND-$INDEX" OMP_NUM_THREADS=4 \
 "$ENV/bin/python" "$SRC/cluster/prometheus/candidate_value_worker.py" \
 --source "$SRC" --run "$RUN" --approval "$APPROVAL" --capsule "$CAPSULE" \
 --source-sha "$SOURCE_SHA" --kind "$KIND" --index "$INDEX"
