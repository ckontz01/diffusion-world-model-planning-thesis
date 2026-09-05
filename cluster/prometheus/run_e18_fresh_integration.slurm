#!/usr/bin/env bash
#SBATCH --job-name=e18-fresh-integration
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/e18-fresh-integration-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/e18-fresh-integration-%j.err
set -euo pipefail
: "${SNAPSHOT:?}" "${RUN_ROOT:?}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
R1=$ROOT/snapshots/gdp-cem-e19-r1-549757ef959a79ba
E18=$ROOT/snapshots/gdp-cem-e18-182ed1e7d1e99946
CORE=$ROOT/snapshots/gdp-cem-e19-r3-30215e7fcfd0e614
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
envdir=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
case "$SNAPSHOT" in "$ROOT"/snapshots/e18-fresh-integration-*) ;; *) exit 2;; esac
case "$RUN_ROOT" in "$ROOT"/experiments/e18-fresh-integration/run-*) ;; *) exit 2;; esac
test ! -w "$SNAPSHOT"
test ! -e "$RUN_ROOT"
for source in "$SNAPSHOT" "$CORE" "$R1" "$E18"; do
  (cd "$source" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done
cmp "$SNAPSHOT/pusht_fresh_initialization.py" "$CORE/pusht_fresh_initialization.py"
mkdir -p "$RUN_ROOT/tmp"
export APPTAINER_TMPDIR="$RUN_ROOT/tmp" APPTAINER_CACHEDIR="$ROOT/tmp/apptainer-cache"
for arm in vad_greedy_300 vad_greedy_576 vad_continuation diagonal_gaussian_continuation direct_gmm_continuation; do
  apptainer exec --nv --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN_ROOT:$RUN_ROOT:rw" \
    --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
    "$IMAGE" env PATH="$envdir/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
    PYTHONPATH="$SNAPSHOT:$R1:$E18:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm" \
    SDL_VIDEODRIVER=dummy CUBLAS_WORKSPACE_CONFIG=:4096:8 MPLBACKEND=Agg \
    MPLCONFIGDIR="$RUN_ROOT/tmp/mpl" TMPDIR="$RUN_ROOT/tmp" \
    "$envdir/bin/python" "$SNAPSHOT/check_e18_fresh_integration.py" --arm "$arm" --output "$RUN_ROOT/$arm"
done
for source in "$SNAPSHOT" "$CORE" "$R1" "$E18"; do
  (cd "$source" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done
