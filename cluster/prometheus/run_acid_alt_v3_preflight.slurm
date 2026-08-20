#!/usr/bin/env bash
#SBATCH --job-name=acid-v3-preflight
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-preflight-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-preflight-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable v3 snapshot path}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
CODE=${ROOT}/src/hi-lewm
OUT=${ROOT}/results/acid-alternative/v3-d2/preflight/job-${SLURM_JOB_ID}
test ! -e "${OUT}"
mkdir -p "${OUT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256)

arguments=(
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md"
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256"
  --trainer-source "${SNAPSHOT}/train_residual_diffusion_pilot_20260816.py"
  --output "${OUT}/preflight.json"
)
for task in pusht reacher cube; do
  for condition in true shuffled_action; do
    summary=${ROOT}/results/acid-alternative/scorers-v2-residual-diffusion-pilot/${task}/${condition}/seed-6101-job-297483
    case "${task}/${condition}" in
      pusht/true) summary=${summary}-0/summary.json ;;
      pusht/shuffled_action) summary=${summary}-1/summary.json ;;
      reacher/true) summary=${summary}-2/summary.json ;;
      reacher/shuffled_action) summary=${summary}-3/summary.json ;;
      cube/true) summary=${summary}-4/summary.json ;;
      cube/shuffled_action) summary=${summary}-5/summary.json ;;
    esac
    arguments+=(--residual "${task}" "${condition}" 6101 "${summary}")
  done
done
for task in pusht reacher cube; do
  case "${task}" in
    pusht) scorer_job=296631; reach_job=296633 ;;
    reacher) scorer_job=296650; reach_job=296652 ;;
    cube) scorer_job=296669; reach_job=296671 ;;
  esac
  for offset in 0 1 2; do
    seed=$((6101 + offset))
    arguments+=(--core "${task}" acid "${seed}" "${ROOT}/results/acid-alternative/scorers/${task}/acid/true/seed-${seed}-job-${scorer_job}-${offset}/best.pt")
    diffusion_index=$((offset + 3))
    arguments+=(--core "${task}" diffusion "${seed}" "${ROOT}/results/acid-alternative/scorers/${task}/diffusion/true/seed-${seed}-job-${scorer_job}-${diffusion_index}/best.pt")
    forward_index=$((offset + 6))
    arguments+=(--core "${task}" forward "${seed}" "${ROOT}/results/acid-alternative/scorers/${task}/forward/true/seed-${seed}-job-${scorer_job}-${forward_index}/best.pt")
    arguments+=(--core "${task}" reachability "${seed}" "${ROOT}/results/acid-alternative/scorers/${task}/reachability/true/seed-${seed}-job-${reach_job}-${offset}/best.pt")
  done
done

apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PATH="${ENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="${SNAPSHOT}:${CODE}:${CODE}/third_party/lewm" \
  PYTHONHASHSEED=0 "${ENV_DIR}/bin/python" "${SNAPSHOT}/preflight_acid_alt_v3.py" "${arguments[@]}"
printf '%s\n' "snapshot=${SNAPSHOT}" "job_id=${SLURM_JOB_ID}" "protected_c1_i1_read=false" > "${OUT}/provenance.txt"
sha256sum "${OUT}/preflight.json" "${OUT}/provenance.txt" > "${OUT}/sha256.txt"
