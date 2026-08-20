#!/usr/bin/env bash
#SBATCH --job-name=gdp-e8d-d2
#SBATCH --partition=a6000
#SBATCH --account=superworld
#SBATCH --qos=normal-a6000
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=16:00:00
#SBATCH --array=0-29%4
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e8d-d2-%A-%a.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e8d-d2-%A-%a.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E8D snapshot}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
TOOLS_DIR=${ROOT}/envs/hi-lewm-tools
task_index=$((SLURM_ARRAY_TASK_ID / 10))
arm_index=$((SLURM_ARRAY_TASK_ID % 10))
case "${task_index}" in
  0) TASK=pusht; DATASET_NAME=pusht_expert_train; DATASET=pusht_expert_train.h5; POLICY=pusht/lewm_hf_22b330c; CHECKPOINT=pusht/lewm_hf_22b330c_object.ckpt; CORE_JOB=296631; PROPOSAL_BASE=0 ;;
  1) TASK=reacher; DATASET_NAME=dmc/reacher_random; DATASET=reacher.h5; POLICY=reacher/lewm; CHECKPOINT=reacher/lewm_object.ckpt; CORE_JOB=296650; PROPOSAL_BASE=3 ;;
  2) TASK=cube; DATASET_NAME=ogbench/cube_single_expert; DATASET=cube_single_expert.h5; POLICY=cube/lewm_hf_b0747c5; CHECKPOINT=cube/lewm_hf_b0747c5_object.ckpt; CORE_JOB=296669; PROPOSAL_BASE=6 ;;
  *) exit 2 ;;
esac
ARMS=(b0 custom_b0 acid gaussian_refresh gadr_shuffled_refresh gadr_true_refresh gadr_true_first gaussian_select gadr_shuffled_select gadr_true_select)
ARM=${ARMS[${arm_index}]}
model_arguments=()
if [[ "${ARM}" = acid ]]; then
  model_arguments+=(--acid-checkpoint "${ROOT}/results/acid-alternative/scorers/${TASK}/acid/true/seed-6101-job-${CORE_JOB}-0/best.pt")
elif [[ "${ARM}" = gaussian_* || "${ARM}" = gadr_* ]]; then
  conditions=(diffusion_true diffusion_shuffled_goal gaussian_true)
  for offset in 0 1 2; do
    condition=${conditions[${offset}]}
    index=$((PROPOSAL_BASE + offset))
    model_arguments+=(--proposal-summary "${condition}" "${ROOT}/results/acid-alternative/gdp-cem-e7p-proposals/${TASK}/${condition}/seed-6101-job-297703-${index}/summary.json")
  done
fi
MANIFEST_DIR=${ROOT}/manifests/acid-alternative-v3-d2/${TASK}/job-297535
E8A=${ROOT}/results/acid-alternative/gdp-cem-e8a-refinement/analysis/job-297721/summary.json
OUT=${ROOT}/results/acid-alternative/gdp-cem-e8d-d2/${TASK}/${ARM}/job-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
JOB_TMP=/tmp/ckontzias-gdp-e8d-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test ! -e "${OUT}"
mkdir -p "${OUT}" "${JOB_TMP}/apptainer"
trap 'rm -rf -- "${JOB_TMP}"' EXIT
export APPTAINER_TMPDIR=${JOB_TMP}/apptainer APPTAINER_CACHEDIR=${ROOT}/tmp/apptainer-cache
nvidia-smi
apptainer exec --nv --cleanenv --bind "${ROOT}:${ROOT}" --bind "${JOB_TMP}:${JOB_TMP}" \
  --bind /usr/share/glvnd/egl_vendor.d/10_nvidia.json:/usr/share/glvnd/egl_vendor.d/10_nvidia.json:ro \
  "${IMAGE}" env PATH="${TOOLS_DIR}/bin:${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}:${ROOT}/src/hi-lewm:${ROOT}/src/hi-lewm/third_party/lewm" \
  PYTHONHASHSEED=8301 CUBLAS_WORKSPACE_CONFIG=:4096:8 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl \
  SDL_VIDEODRIVER=dummy MPLBACKEND=Agg SLURM_JOB_ID="${SLURM_JOB_ID}" \
  SLURM_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID}" TMPDIR="${JOB_TMP}" \
  "${ENV_DIR}/bin/python" "${SNAPSHOT}/evaluate_gdp_cem_e8d_closed_loop.py" \
  --task "${TASK}" --arm "${ARM}" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E8D-GADR-EXPOSED-D2-CLOSED-LOOP-PROTOCOL-2026-08-17.md" \
  --method-protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" --e8a-aggregate "${E8A}" \
  --code-root "${ROOT}/src/hi-lewm" --stablewm-home "${ROOT}/data/stablewm" \
  --dataset "${ROOT}/data/stablewm/${DATASET}" --dataset-name "${DATASET_NAME}" \
  --world-model-policy "${POLICY}" --world-model-checkpoint "${ROOT}/data/stablewm/${CHECKPOINT}" \
  --eval-manifest "${MANIFEST_DIR}/d2-fresh.tsv" --eval-provenance "${MANIFEST_DIR}/provenance.json" \
  "${model_arguments[@]}" --output-dir "${OUT}"
printf '%s\n' "study=gdp_cem_e8d_exposed_d2" "task=${TASK}" "arm=${ARM}" \
  "job_id=${SLURM_JOB_ID}" "d2_read=true" "d3_read=false" \
  "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/summary.json" "${OUT}/episodes.tsv" \
  "${OUT}/solver-diagnostics.jsonl" "${OUT}/proposal-diagnostics.jsonl" \
  "${OUT}/cost-diagnostics.jsonl" "${OUT}/resolved-config.json" \
  "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
