#!/usr/bin/env bash
set -euo pipefail
[[ $# == 5 && -n ${SLURM_JOB_ID:-} ]] || exit 2
SRC=$(realpath "$1"); RUN=$(realpath "$2"); APPROVAL=$(realpath "$3"); KIND=$4; INDEX=$5
ROOT=/lustreFS/data/superworld/ckontzias/thesis
[[ "$RUN" == "$ROOT/experiments/candidate-value-breadth-precision-20260915/run-"* ]] || exit 2
[[ "$KIND" =~ ^(breadth|precision|evaluation|fit|analyze)$ && "$INDEX" =~ ^[0-9]+$ ]] || exit 2
(cd "$SRC" && sha256sum --check --quiet SOURCE-MANIFEST.sha256)
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
mkdir "$RUN/tmp-$KIND-$INDEX"
NV=(); DEVICE=()
case "$KIND" in breadth|precision|evaluation) NV=(--nv);; *) DEVICE=(CUDA_VISIBLE_DEVICES=);; esac
ulimit -f 524288
apptainer exec "${NV[@]}" --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN:$RUN:rw" "$IMAGE" env \
 PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 SLURM_JOB_ID="$SLURM_JOB_ID" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
 PYTHONPATH="$SRC/cluster/prometheus:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm" \
 SDL_VIDEODRIVER=dummy CUBLAS_WORKSPACE_CONFIG=:4096:8 MPLBACKEND=Agg \
 MPLCONFIGDIR="$RUN/tmp-$KIND-$INDEX/mpl" TMPDIR="$RUN/tmp-$KIND-$INDEX" \
 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 "${DEVICE[@]}" \
 "$ENV/bin/python" "$SRC/cluster/prometheus/breadth_precision_execute.py" worker \
 --source "$SRC" --run "$RUN" --approval "$APPROVAL" --kind "$KIND" --index "$INDEX"
