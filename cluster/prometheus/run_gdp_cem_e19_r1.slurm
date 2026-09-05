#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-r1
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-r1-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-r1-%j.err
set -euo pipefail
: "${SNAPSHOT:?}" "${RUN_ROOT:?}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
PARENT=${ROOT}/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0
E18=${ROOT}/snapshots/gdp-cem-e18-182ed1e7d1e99946
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
case "$SNAPSHOT" in "$ROOT"/snapshots/gdp-cem-e19-r1-*) ;; *) exit 2;; esac
case "$RUN_ROOT" in "$ROOT"/experiments/gdp-cem-e19-r1/run-*) ;; *) exit 2;; esac
test ! -w "$SNAPSHOT"
test ! -e "$RUN_ROOT/preparation"
(cd "$SNAPSHOT" && sha256sum -c SOURCE-MANIFEST.sha256)
(cd "$PARENT" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "$E18" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
(cd "$ROOT/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988/preparation" && sha256sum -c sha256.txt >/dev/null)
mkdir -p "$RUN_ROOT/tmp"
export APPTAINER_TMPDIR="$RUN_ROOT/tmp" APPTAINER_CACHEDIR="$ROOT/tmp/apptainer-cache"
run_python() {
  local stack=$1; shift
  local envdir pythonpath
  if [ "$stack" = sage ]; then
    envdir=$ROOT/envs/sage-official-py310-torch251-cu121
    pythonpath=$SNAPSHOT:$PARENT/official-sage:$PARENT
  else
    envdir=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
    pythonpath=$SNAPSHOT:$E18:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm
  fi
  apptainer exec --nv --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN_ROOT:$RUN_ROOT:rw" \
    --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
    "$IMAGE" env PATH="$envdir/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
    PYTHONPATH="$pythonpath" MUJOCO_GL=egl PYOPENGL_PLATFORM=egl SDL_VIDEODRIVER=dummy \
    CUBLAS_WORKSPACE_CONFIG=:4096:8 MPLBACKEND=Agg MPLCONFIGDIR="$RUN_ROOT/tmp/mpl" TMPDIR="$RUN_ROOT/tmp" \
    "$envdir/bin/python" "$@"
}
run_python sage -m pytest -q -p no:cacheprovider "$SNAPSHOT/test_gdp_cem_e19_r1.py"
run_python sage "$SNAPSHOT/gdp_cem_e19_r1.py" prepare --output "$RUN_ROOT/preparation"
for stack in sage e18; do
  for caseid in 0 1 2 3 4; do
    for repeat in 0 1; do
      run_python "$stack" "$SNAPSHOT/gdp_cem_e19_r1.py" execute \
        --prepared "$RUN_ROOT/preparation/STIMULI.json" --stack "$stack" --case "$caseid" --repeat "$repeat" \
        --output "$RUN_ROOT/$stack/case-$caseid/repeat-$repeat/TRACE.json"
    done
  done
done
