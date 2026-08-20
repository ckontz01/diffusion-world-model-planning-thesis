#!/usr/bin/env bash
#SBATCH --job-name=acid-v3-d2-manifest
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-d2-manifest-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/acid-v3-d2-manifest-%j.err

set -euo pipefail
: "${SNAPSHOT:?submit with immutable v3 snapshot path}"
: "${P1_GATE_JOB_ID:?submit with passing P1 gate job ID}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
IMAGE=${ROOT}/containers/pytorch-2.5.1-cuda12.1-cudnn9-runtime.sif
ENV_DIR=${ROOT}/envs/hi-lewm-artifact-py311-cu121-swm006
GATE=${ROOT}/results/acid-alternative/v3-d2/p1-gate/job-${P1_GATE_JOB_ID}/gate.json
test -f "${GATE}"
apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
  PYTHONNOUSERSITE=1 "${ENV_DIR}/bin/python" - "${GATE}" <<'PY'
import json, sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
assert value["kind"] == "acid_alt_v3_multiseed_p1_gate"
assert value["decision"] == "authorize_D2" and value["all_pass"] is True
assert value["protected_c1_i1_read"] is False
PY

for task in pusht reacher cube; do
  case "${task}" in
    pusht) dataset=pusht_expert_train.h5 ;;
    reacher) dataset=reacher.h5 ;;
    cube) dataset=cube_single_expert.h5 ;;
  esac
  OUT=${ROOT}/manifests/acid-alternative-v3-d2/${task}/job-${SLURM_JOB_ID}
  test ! -e "${OUT}"
  mkdir -p "${OUT}"
  apptainer exec --cleanenv --bind "${ROOT}:${ROOT}" "${IMAGE}" env \
    PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SNAPSHOT}" \
    "${ENV_DIR}/bin/python" "${SNAPSHOT}/create_acid_alt_d2_manifest.py" \
    --task "${task}" --dataset "${ROOT}/data/stablewm/${dataset}" \
    --partition-manifest "${ROOT}/manifests/partitions/${task}-v1/episodes-seed-20260728.tsv" \
    --r0-manifest "${ROOT}/manifests/acid-alternative-v1/${task}/r0-official-seed42.tsv" \
    --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-V3-MULTISEED-D2-PROTOCOL-2026-08-16.md" \
    --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
    --output-tsv "${OUT}/d2-fresh.tsv" --output-json "${OUT}/provenance.json"
  sha256sum "${OUT}/d2-fresh.tsv" "${OUT}/provenance.json" > "${OUT}/sha256.txt"
done
