#!/usr/bin/env bash
set -euo pipefail
[[ $# == 3 && -n ${SLURM_JOB_ID:-} ]] || exit 2
SRC=$(realpath "$1"); OUT=$(realpath "$2"); SOURCE_SHA=$3
ROOT=/lustreFS/data/superworld/ckontzias/thesis
[[ "$OUT" == "$ROOT/staging/single-anchor-ranking-20260914/"* ]] || exit 2
[[ $(sha256sum "$SRC/SOURCE-MANIFEST.sha256" | cut -d' ' -f1) == "$SOURCE_SHA" ]] || exit 2
(cd "$SRC" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
HIST=$ROOT/snapshots/independent-pusht-4a608e5
INTEGRATION=$ROOT/snapshots/e18-fresh-integration-a9d1c26573158f93
R1=$ROOT/snapshots/gdp-cem-e19-r1-549757ef959a79ba
E18=$ROOT/snapshots/gdp-cem-e18-182ed1e7d1e99946
IMPORT_PATH="$SRC/cluster/prometheus:$HIST:$INTEGRATION:$R1:$E18:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm"
HOST_STATUS=0; CONTAINER_STATUS=0
env PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONPATH="$IMPORT_PATH" /usr/bin/python3 \
 "$SRC/cluster/prometheus/preflight_single_anchor_ranking.py" --mode host-dispatcher \
 --out "$OUT/HOST-DISPATCHER.json" || HOST_STATUS=$?
apptainer exec --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$OUT:$OUT:rw" "$IMAGE" env \
 PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH="$IMPORT_PATH" \
 CUDA_VISIBLE_DEVICES='' SDL_VIDEODRIVER=dummy MPLBACKEND=Agg MPLCONFIGDIR="$OUT/mpl" \
 TMPDIR="$OUT" OMP_NUM_THREADS=2 "$ENV/bin/python" \
 "$SRC/cluster/prometheus/preflight_single_anchor_ranking.py" --mode pinned-container \
 --out "$OUT/PINNED-CONTAINER.json" || CONTAINER_STATUS=$?
(cd "$OUT" && sha256sum HOST-DISPATCHER.json PINNED-CONTAINER.json > sha256.txt)
[[ $HOST_STATUS == 0 && $CONTAINER_STATUS == 0 ]]
