#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-r3-arms
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-r3-arms-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-r3-arms-%j.err
set -euo pipefail
: "${SNAPSHOT:?}" "${RUN_ROOT:?}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
PARENT=$ROOT/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0
R1=$ROOT/snapshots/gdp-cem-e19-r1-549757ef959a79ba
E18=$ROOT/snapshots/gdp-cem-e18-182ed1e7d1e99946
CORE=$ROOT/snapshots/gdp-cem-e19-r3-30215e7fcfd0e614
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
case "$SNAPSHOT" in "$ROOT"/snapshots/gdp-cem-e19-r3-arms-*) ;; *) exit 2;; esac
case "$RUN_ROOT" in "$ROOT"/experiments/gdp-cem-e19-r3/arms-*) ;; *) exit 2;; esac
test ! -w "$SNAPSHOT"
test ! -e "$RUN_ROOT"
cmp "$SNAPSHOT/pusht_fresh_initialization.py" "$CORE/pusht_fresh_initialization.py"
for source in "$SNAPSHOT" "$CORE" "$R1" "$PARENT" "$E18"; do
  (cd "$source" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done
mkdir -p "$RUN_ROOT/tmp"
export APPTAINER_TMPDIR="$RUN_ROOT/tmp" APPTAINER_CACHEDIR="$ROOT/tmp/apptainer-cache"
for stack in sage e18; do
  if [ "$stack" = sage ]; then
    envdir=$ROOT/envs/sage-official-py310-torch251-cu121
    pythonpath=$SNAPSHOT:$R1:$PARENT/lewm-serialization-compat:$PARENT/official-sage:$PARENT:$PARENT/lewm-runtime
    arms=(base_cem far_goal_prior_cem lewm_generator generator_prior_top sage)
  else
    envdir=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
    pythonpath=$SNAPSHOT:$R1:$E18:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm
    arms=(vad_greedy_300 vad_greedy_576 vad_continuation diagonal_gaussian_continuation direct_gmm_continuation)
  fi
  for arm in "${arms[@]}"; do
    apptainer exec --nv --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN_ROOT:$RUN_ROOT:rw" \
      --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
      "$IMAGE" env PATH="$envdir/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
      PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
      PYTHONPATH="$pythonpath" SDL_VIDEODRIVER=dummy MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
      CUBLAS_WORKSPACE_CONFIG=:4096:8 MPLBACKEND=Agg MPLCONFIGDIR="$RUN_ROOT/tmp/mpl" TMPDIR="$RUN_ROOT/tmp" \
      "$envdir/bin/python" "$SNAPSHOT/gdp_cem_e19_r3_arms.py" --stack "$stack" --arm "$arm" \
        --output "$RUN_ROOT/$stack/$arm"
  done
done
for source in "$SNAPSHOT" "$CORE" "$R1" "$PARENT" "$E18"; do
  (cd "$source" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done
