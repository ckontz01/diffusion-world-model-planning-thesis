#!/usr/bin/env bash
#SBATCH --job-name=acid-v3-core-score
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --array=0-2%3
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-core-score-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-core-score-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable v3 snapshot path}"
: "${CAPTURE_JOB_ID:?submit with capture array ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
CODE=${ROOT}/src/hi-lewm
STABLEWM_HOME=${ROOT}/data/stablewm
case "${SLURM_ARRAY_TASK_ID}" in
  0) TASK=pusht; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; SCORER_JOB=296631; REACH_JOB=296633 ;;
  1) TASK=reacher; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; SCORER_JOB=296650; REACH_JOB=296652 ;;
  2) TASK=cube; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; SCORER_JOB=296669; REACH_JOB=296671 ;;
  *) exit 2 ;;
esac
CAPTURE=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/capture/planner-seed-8201-job-${CAPTURE_JOB_ID}-${SLURM_ARRAY_TASK_ID}
OUT=${ROOT}/results/acid-alternative/v3-d2/stage-a/${TASK}/shared-score/job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-acid-v3-core-score-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
arguments=()
for offset in 0 1 2; do
  seed=$((6101 + offset)); forward_index=$((offset + 6)); diffusion_index=$((offset + 3))
  arguments+=(--scorer "forward_true_seed_${seed}=forward=${ROOT}/results/acid-alternative/scorers/${TASK}/forward/true/seed-${seed}-job-${SCORER_JOB}-${forward_index}/best.pt")
  arguments+=(--scorer "legacy_dtv_true_seed_${seed}=diffusion=${ROOT}/results/acid-alternative/scorers/${TASK}/diffusion/true/seed-${seed}-job-${SCORER_JOB}-${diffusion_index}/best.pt")
  arguments+=(--scorer "reachability_true_seed_${seed}=reachability=${ROOT}/results/acid-alternative/scorers/${TASK}/reachability/true/seed-${seed}-job-${REACH_JOB}-${offset}/best.pt")
done
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" "${IMAGE}" env \
  PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=0 CUBLAS_WORKSPACE_CONFIG=:4096:8 SLURM_JOB_ID="${SLURM_JOB_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" -m acid_alternative_diagnostics.score_candidate_pools \
  --candidate-artifact "${CAPTURE}/candidate-pools.pt" --candidate-manifest "${CAPTURE}/manifest.json" \
  --stablewm-home "${STABLEWM_HOME}" --world-model-policy "${POLICY}" \
  --world-model-checkpoint "${STABLEWM_HOME}/${CHECKPOINT}" --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --lambda-weight 0.07 "${arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "task=${TASK}" "analysis_role=D2" "capture_array=${CAPTURE_JOB_ID}" "job_id=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/candidate-scores.pt" "${OUT}/manifest.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
