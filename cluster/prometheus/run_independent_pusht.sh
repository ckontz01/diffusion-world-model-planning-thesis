#!/usr/bin/env bash
set -euo pipefail
ROOT=/lustreFS/data/superworld/ckontzias/thesis
NEW=$(cd -- "$(dirname -- "$0")" && pwd)
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
INTEGRATION=$ROOT/snapshots/e18-fresh-integration-a9d1c26573158f93
E18=$ROOT/snapshots/gdp-cem-e18-182ed1e7d1e99946
R1=$ROOT/snapshots/gdp-cem-e19-r1-549757ef959a79ba
SAGE=$ROOT/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0/official-sage
RUN=$1; shift
mkdir -p "$RUN/tmp"
(cd "$NEW" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
GPU_ARGS=(); if [[ ${USE_GPU:-0} == 1 ]]; then GPU_ARGS+=(--nv); fi
apptainer exec "${GPU_ARGS[@]}" --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN:$RUN:rw" \
 "$IMAGE" env PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 PYTHONPATH="$NEW:$INTEGRATION:$R1:$E18:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm" \
 SDL_VIDEODRIVER=dummy CUBLAS_WORKSPACE_CONFIG=:4096:8 MPLBACKEND=Agg \
 MPLCONFIGDIR="$RUN/tmp/mpl" TMPDIR="$RUN/tmp" OMP_NUM_THREADS=4 \
 "$ENV/bin/python" "$@"
