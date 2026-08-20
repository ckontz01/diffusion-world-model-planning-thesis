#!/usr/bin/env bash
#SBATCH --job-name=gdp-e11-d3-manifest
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=12G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e11-d3-manifest-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e11-d3-manifest-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E11 snapshot}"
: "${PREFLIGHT_JOB_ID:?missing successful E11 preflight job}"
: "${SMOKE_JOB_ID:?missing successful E11 P1 smoke job}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
PREFLIGHT=${ROOT}/results/acid-alternative/gdp-cem-e11-preflight/job-${PREFLIGHT_JOB_ID}
SMOKE=${ROOT}/results/acid-alternative/gdp-cem-e11-p1-smoke/job-${SMOKE_JOB_ID}
sha256sum -c "${PREFLIGHT}/sha256.txt" >/dev/null
sha256sum -c "${SMOKE}/sha256.txt" >/dev/null
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 "${ENV_DIR}/bin/python" - "${PREFLIGHT}/preflight.json" \
  "${SMOKE}/summary.json" <<'PY'
import json, sys
preflight = json.load(open(sys.argv[1], encoding="utf-8"))
smoke = json.load(open(sys.argv[2], encoding="utf-8"))
assert preflight["status"] == "ok"
assert preflight["kind"] == "gdp_cem_e11_outcome_free_preflight"
assert preflight["d3_read"] is False and preflight["protected_c1_i1_read"] is False
assert smoke["status"] == "ok"
assert smoke["kind"] == "gdp_cem_e11_p1_closed_loop_integration_smoke"
assert smoke["d3_read"] is False and smoke["protected_c1_i1_read"] is False
PY
for task in pusht reacher cube; do
  case "${task}" in
    pusht) dataset=pusht_expert_train.h5 ;;
    reacher) dataset=reacher.h5 ;;
    cube) dataset=cube_single_expert.h5 ;;
  esac
  OUT=${ROOT}/manifests/gdp-cem-e11-d3/${task}/job-${SLURM_JOB_ID}
  test ! -e "${OUT}"
  mkdir -p "${OUT}"
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
    "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_gdp_cem_e11_d3_manifest.py" \
    --task "${task}" --dataset "${ROOT}/data/stablewm/${dataset}" \
    --partition-manifest "${ROOT}/manifests/partitions/${task}-v1/episodes-seed-20260728.tsv" \
    --exclusion r0 "${ROOT}/manifests/acid-alternative-v1/${task}/r0-official-seed42.tsv" \
    --exclusion d1 "${ROOT}/manifests/acid-alternative-v1/${task}/d1-fresh-development.tsv" \
    --exclusion d2 "${ROOT}/manifests/acid-alternative-v3-d2/${task}/job-297535/d2-fresh.tsv" \
    --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E11-PURE-VELOCITY-UNTOUCHED-D3-PROTOCOL-2026-08-17.md" \
    --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
    --output-tsv "${OUT}/d3-untouched.tsv" \
    --output-json "${OUT}/provenance.json"
  printf '%s\n' "study=gdp_cem_e11_d3_manifest" "task=${task}" \
    "job_id=${SLURM_JOB_ID}" "identifier_inputs_only=true" \
    "preflight_job_id=${PREFLIGHT_JOB_ID}" "p1_smoke_job_id=${SMOKE_JOB_ID}" \
    "outcome_columns_read=false" "protected_c1_i1_read=false" \
    > "${OUT}/audit.txt"
  sha256sum "${OUT}/d3-untouched.tsv" "${OUT}/provenance.json" \
    "${OUT}/audit.txt" > "${OUT}/sha256.txt"
  chmod a-w "${OUT}/d3-untouched.tsv" "${OUT}/provenance.json" \
    "${OUT}/audit.txt" "${OUT}/sha256.txt" "${OUT}"
done
