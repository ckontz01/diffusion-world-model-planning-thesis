#!/usr/bin/env bash
#SBATCH --job-name=gdp-e19-overlap
#SBATCH --partition=defq
#SBATCH --account=superworld
#SBATCH --qos=normal
#SBATCH --cpus-per-task=16
#SBATCH --mem=192G
#SBATCH --time=12:00:00
#SBATCH --output=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-overlap-%j.out
#SBATCH --error=/lustreFS/data/superworld/ckontzias/thesis/logs/gdp-e19-overlap-%j.err

set -euo pipefail
: "${SNAPSHOT:?missing immutable E19 snapshot}"
: "${RUN_ROOT:?missing unique E19 run root}"
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
SAGE=${SNAPSHOT}/official-sage
STABLEWM=${ROOT}/data/stablewm
E14=${ROOT}/experiments/gdp-cem-e14/development-run-20260823-99f92cbe
E15=${ROOT}/experiments/gdp-cem-e15
E16=${ROOT}/experiments/gdp-cem-e16/development-run-20260827-3669dc32
E17=${ROOT}/experiments/gdp-cem-e17/development-run-20260827-9fb5a8c2
E18=${ROOT}/experiments/gdp-cem-e18/development-run-20260827-182ed1e7
LEWM_SOURCES=${ROOT}/downloads/acid-alternative/flat-lewm-models
E14_PUSHT=${STABLEWM}/derived/acid-alternative-v1/pusht/lewm-hf-22b330c/e14-variable-cache-job-298993-0
E14_CUBE=${STABLEWM}/derived/acid-alternative-v1/cube/lewm-hf-b0747c5/e14-variable-cache-job-298993-1
E15_PUSHT=${E15}/data-preflight-1b97e228/pusht
E15_CUBE=${E15}/data-preflight-1b97e228/cube
E17_PUSHT=${E17}/cache/pusht
E17_CUBE=${E17}/cache/cube
E16_PUSHT=${E16}/stage-a-banks/pusht/vad/seed-7201
E16_CUBE=${E16}/stage-a-banks/cube/vad/seed-7201
OLD_P2=${E14}/p2-manifests/33ae351f
E18_P2=${E18}/p2-manifests
LEWM_OUTPUT=${RUN_ROOT}/lewm-identity
OUTPUT=${RUN_ROOT}/data-overlap-audit

test ! -w "${SNAPSHOT}"
(cd "${SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
(cd "${RUN_ROOT}/preparation" && sha256sum -c sha256.txt >/dev/null)
for directory in \
  "${E14_PUSHT}" "${E14_CUBE}" \
  "${E15_PUSHT}" "${E15_CUBE}" \
  "${E17_PUSHT}" "${E17_CUBE}" \
  "${E16_PUSHT}" "${E16_CUBE}" \
  "${OLD_P2}/pusht" "${OLD_P2}/cube" \
  "${E18_P2}/pusht" "${E18_P2}/cube"; do
  (cd "${directory}" && sha256sum -c sha256.txt >/dev/null)
done
test ! -e "${LEWM_OUTPUT}"
test ! -e "${OUTPUT}"
mkdir -p "${LEWM_OUTPUT}"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export PYTHONPATH=${SNAPSHOT}:${SAGE}
"${ENV_DIR}/bin/python" "${SNAPSHOT}/audit_gdp_cem_e19_lewm_identity.py" \
  --pair "pusht=${STABLEWM}/pusht/lewm_object.ckpt,${STABLEWM}/pusht/lewm_hf_22b330c_object.ckpt" \
  --pair "cube=${STABLEWM}/cube/lewm_object.ckpt,${STABLEWM}/cube/lewm_hf_b0747c5_object.ckpt" \
  --source "pusht=${LEWM_SOURCES}/pusht-22b330c28c27ead4bfd1888615af1340e3fe9052" \
  --source "cube=${LEWM_SOURCES}/cube-b0747c5002e86d2ce8f3cd8178004b97524c587d" \
  --output "${LEWM_OUTPUT}/LEWM-IDENTITY.json"
(cd "${LEWM_OUTPUT}" && sha256sum LEWM-IDENTITY.json > sha256.txt)
chmod -R a-w "${LEWM_OUTPUT}"
"${ENV_DIR}/bin/python" "${SNAPSHOT}/audit_gdp_cem_e19_data_overlap.py" \
  --sage-root "${SAGE}" \
  --stablewm-root "${STABLEWM}" \
  --pusht-lance "${RUN_ROOT}/preparation/pusht_expert_train.lance" \
  --e14-cache "pusht=${E14_PUSHT}/cache.h5" \
  --e14-cache "cube=${E14_CUBE}/cache.h5" \
  --e15-cache "pusht=${E15_PUSHT}/cache.h5" \
  --e15-cache "cube=${E15_CUBE}/cache.h5" \
  --e17-cache "pusht=${E17_PUSHT}/cache.h5" \
  --e17-cache "cube=${E17_CUBE}/cache.h5" \
  --e16-bank "pusht=${E16_PUSHT}/metrics.h5" \
  --e16-bank "cube=${E16_CUBE}/metrics.h5" \
  --old-p2-queries "pusht=${OLD_P2}/pusht/queries.tsv" \
  --old-p2-queries "cube=${OLD_P2}/cube/queries.tsv" \
  --e18-p2-queries "pusht=${E18_P2}/pusht/queries.tsv" \
  --e18-p2-queries "cube=${E18_P2}/cube/queries.tsv" \
  --lewm-identity "${LEWM_OUTPUT}/LEWM-IDENTITY.json" \
  --protocol "${SNAPSHOT}/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-PROTOCOL-2026-08-28.md" \
  --source-manifest "${SNAPSHOT}/SOURCE-MANIFEST.sha256" \
  --output-dir "${OUTPUT}"
(cd "${OUTPUT}" && sha256sum -c sha256.txt >/dev/null)
chmod -R a-w "${OUTPUT}"
