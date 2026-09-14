#!/usr/bin/env bash
# PREPARED ONLY: no sbatch/real validation authorized until researcher approval.
set -euo pipefail
[[ -n ${SLURM_JOB_ID:-} && $# == 6 ]] || exit 2
SRC=$(realpath "$1"); RUN=$(realpath "$2"); APPROVAL=$(realpath "$3")
SOURCE_SHA=$4; PROTOCOL_SHA=$5; INDEX=$6
ROOT=/lustreFS/data/superworld/ckontzias/thesis
[[ "$RUN" == "$ROOT/experiments/single-anchor-ranking-20260914/"* ]] || exit 2
[[ "$APPROVAL" == "$ROOT/"* && "$INDEX" =~ ^[0-9]+$ && "$INDEX" -le 63 ]] || exit 2
[[ $(sha256sum "$SRC/SOURCE-MANIFEST.sha256" | cut -d' ' -f1) == "$SOURCE_SHA" ]] || exit 2
(cd "$SRC" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
HIST=$ROOT/snapshots/independent-pusht-4a608e5
(cd "$HIST" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
INTEGRATION=$ROOT/snapshots/e18-fresh-integration-a9d1c26573158f93
R1=$ROOT/snapshots/gdp-cem-e19-r1-549757ef959a79ba
E18=$ROOT/snapshots/gdp-cem-e18-182ed1e7d1e99946
REFS=(1269 582 525 722 567 716 630 1066 1074 1565 70 867 221 905 1287 621 428 288 1488 757 641 855 1280 420 860 98 886 432 181 783 706 989)
REF=${REFS[$((INDEX/2))]}; REPEAT=$((INDEX%2))
mkdir "$RUN/tmp-$INDEX"
ulimit -f 65536
apptainer exec --nv --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN:$RUN:rw" "$IMAGE" env \
 PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 PYTHONPATH="$SRC/cluster/prometheus:$HIST:$INTEGRATION:$R1:$E18:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm" \
 SDL_VIDEODRIVER=dummy CUBLAS_WORKSPACE_CONFIG=:4096:8 MPLBACKEND=Agg \
 MPLCONFIGDIR="$RUN/tmp-$INDEX/mpl" TMPDIR="$RUN/tmp-$INDEX" OMP_NUM_THREADS=4 \
 "$ENV/bin/python" "$SRC/cluster/prometheus/single_anchor_ranking_runner.py" \
 --reference "$REF" --repeat "$REPEAT" --out "$RUN/ref-$REF-repeat-$REPEAT" \
 --combined "$SRC/docs/bottleneck/receipts/EXTENSION-COMBINED-301071.json" \
 --approval "$APPROVAL" --source "$SRC" --source-sha "$SOURCE_SHA" \
 --protocol "$SRC/docs/single-anchor-ranking-20260914/PROTOCOL.md" --protocol-sha "$PROTOCOL_SHA"
