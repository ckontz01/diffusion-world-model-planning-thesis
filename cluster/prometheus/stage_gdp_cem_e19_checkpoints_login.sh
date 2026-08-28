#!/usr/bin/env bash
set -euo pipefail

SAGE_ROOT=${1:?usage: stage_gdp_cem_e19_checkpoints_login.sh OFFICIAL_SAGE_ROOT}
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
REVISION=1b5afbc8eeb1c8e99d9529099e1aa15f392a6346
DESTINATION=${ROOT}/downloads/gdp-cem-e19/checkpoints-${REVISION}
COMMIT=8219029fd52e89157e05aebb998ab26f0ef46966
TREE=0c64066eeac97c27fee382c1879bb26968b3fd56

SAGE_ROOT=$(cd "${SAGE_ROOT}" && pwd -P)
test "$(git -C "${SAGE_ROOT}" rev-parse HEAD)" = "${COMMIT}"
test "$(git -C "${SAGE_ROOT}" rev-parse 'HEAD^{tree}')" = "${TREE}"
test -z "$(git -C "${SAGE_ROOT}" status --porcelain --untracked-files=all)"
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null

if [[ -d "${DESTINATION}" ]]; then
  test ! -w "${DESTINATION}"
  (cd "${DESTINATION}" && sha256sum -c sha256.txt >/dev/null)
  printf 'checkpoint_root=%s\nstatus=already-complete\n' "${DESTINATION}"
  exit 0
fi

mkdir -p "$(dirname "${DESTINATION}")"
STAGING=$(mktemp -d "$(dirname "${DESTINATION}")/.e19-checkpoints.XXXXXXXX")
cleanup() {
  if [[ -n "${STAGING:-}" && -d "${STAGING}" ]]; then
    case "${STAGING}" in
      "$(dirname "${DESTINATION}")"/.e19-checkpoints.*) rm -rf -- "${STAGING}" ;;
      *) printf 'refusing unsafe cleanup target: %s\n' "${STAGING}" >&2 ;;
    esac
  fi
}
trap cleanup EXIT

export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export PYTHONPATH=${SAGE_ROOT}
export HF_HOME=${ROOT}/downloads/gdp-cem-e19/hf-cache
export HF_HUB_DISABLE_TELEMETRY=1
cd "${SAGE_ROOT}"
"${ENV_DIR}/bin/python" scripts/download_checkpoints.py \
  --repo-id CLTRAY/SAGE \
  --revision "${REVISION}" \
  --out-dir "${STAGING}" \
  --registry "${SAGE_ROOT}/configs/checkpoints.json"

"${ENV_DIR}/bin/python" - "${STAGING}" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
registry = json.loads(
    Path("configs/checkpoints.json").read_text(encoding="utf-8")
)
rows = []
for key, entry in sorted(registry.items()):
    path = root / entry["filename"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != entry["size_bytes"] or digest != entry["sha256"]:
        raise RuntimeError(f"checkpoint mismatch after download: {key}")
    rows.append(
        {
            "key": key,
            "filename": entry["filename"],
            "bytes": path.stat().st_size,
            "sha256": digest,
        }
    )
payload = {
    "kind": "gdp_cem_e19_login_node_checkpoint_staging",
    "official_sage_commit": "8219029fd52e89157e05aebb998ab26f0ef46966",
    "huggingface_repository": "CLTRAY/SAGE",
    "huggingface_revision": "1b5afbc8eeb1c8e99d9529099e1aa15f392a6346",
    "checkpoints": rows,
    "scientific_modification": False,
    "performance_metric_read": False,
    "d5_read": False,
}
(root / "CHECKPOINT-STAGING.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

(cd "${STAGING}" && {
  sha256sum \
    pusht_generator.pt pusht_action_prior.pt pusht_far_action_prior.pt \
    cube_generator.pt cube_action_prior.pt cube_far_action_prior.pt \
    CHECKPOINT-STAGING.json > sha256.txt
  sha256sum -c sha256.txt >/dev/null
})
chmod -R a-w "${STAGING}"
mv -- "${STAGING}" "${DESTINATION}"
STAGING=
test ! -w "${DESTINATION}"
(cd "${DESTINATION}" && sha256sum -c sha256.txt >/dev/null)
printf 'checkpoint_root=%s\nstatus=created\n' "${DESTINATION}"
