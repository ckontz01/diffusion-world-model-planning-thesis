#!/usr/bin/env bash
#SBATCH --job-name=e18-design-timing
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=00:20:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/e18-design-timing-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/e18-design-timing-%j.err
set -euo pipefail
ROOT=/lustreFS/data/superworld/ckontzias/thesis
NEW=$ROOT/staging/e18-design-feasibility-20260905
INTEGRATION=$ROOT/snapshots/e18-fresh-integration-a9d1c26573158f93
R1=$ROOT/snapshots/gdp-cem-e19-r1-549757ef959a79ba
E18=$ROOT/snapshots/gdp-cem-e18-182ed1e7d1e99946
RUN=$ROOT/experiments/e18-design-feasibility/timing-job-$SLURM_JOB_ID
IMAGE=$ROOT/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV=$ROOT/envs/hi-lewm-artifact-py311-cu121-swm006
test ! -e "$RUN"
mkdir -p "$RUN/tmp"
for source in "$INTEGRATION" "$R1" "$E18"; do
  (cd "$source" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
done
apptainer exec --nv --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN:$RUN:rw" \
 --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
 "$IMAGE" env PATH="$ENV/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
 PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
 PYTHONPATH="$NEW:$INTEGRATION:$R1:$E18:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm" \
 SDL_VIDEODRIVER=dummy CUBLAS_WORKSPACE_CONFIG=:4096:8 MPLBACKEND=Agg \
 MPLCONFIGDIR="$RUN/tmp/mpl" TMPDIR="$RUN/tmp" \
 "$ENV/bin/python" "$NEW/e18_design_timing.py" --out "$RUN/timing.json"
apptainer exec --cleanenv --bind "$ROOT:$ROOT:ro" --bind "$RUN:$RUN:rw" \
 "$IMAGE" env PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
 PYTHONPATH="$NEW:$INTEGRATION:$R1:$E18:$ROOT/src/hi-lewm:$ROOT/src/hi-lewm/third_party/lewm" \
 SDL_VIDEODRIVER=dummy MPLBACKEND=Agg MPLCONFIGDIR="$RUN/tmp/mpl" TMPDIR="$RUN/tmp" \
 "$ENV/bin/python" -m pytest -q -p no:cacheprovider "$NEW/test_e18_full_budget_lifecycle.py" > "$RUN/lifecycle-tests.txt"
(cd "$RUN" && sha256sum timing.json lifecycle-tests.txt > sha256.txt)
