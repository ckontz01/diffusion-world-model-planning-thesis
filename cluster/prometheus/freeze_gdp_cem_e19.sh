#!/usr/bin/env bash
set -euo pipefail

STAGED_ROOT=${1:?usage: freeze_gdp_cem_e19.sh STAGED_ROOT OFFICIAL_SAGE LEWM_RUNTIME OUTPUT_PARENT}
OFFICIAL_SAGE=${2:?usage: freeze_gdp_cem_e19.sh STAGED_ROOT OFFICIAL_SAGE LEWM_RUNTIME OUTPUT_PARENT}
LEWM_RUNTIME=${3:?usage: freeze_gdp_cem_e19.sh STAGED_ROOT OFFICIAL_SAGE LEWM_RUNTIME OUTPUT_PARENT}
OUTPUT_PARENT=${4:?usage: freeze_gdp_cem_e19.sh STAGED_ROOT OFFICIAL_SAGE LEWM_RUNTIME OUTPUT_PARENT}
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
COMMIT=8219029fd52e89157e05aebb998ab26f0ef46966
TREE=0c64066eeac97c27fee382c1879bb26968b3fd56
LEWM_RUNTIME_COMMIT=8edfeb336732b5f3ce7b8b210d0ba370a09e2cac
LEWM_RUNTIME_TREE=40444957371d400fe9ac24db3f9d453081a35bea
PROTOCOL=ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-REPRODUCTION-AND-OVERLAP-PROTOCOL-2026-08-28.md

FILES=(
  "${PROTOCOL}"
  E19-OFFICIAL-SAGE-RELEASE-DEFECTS-2026-08-28.md
  E19-IMPLEMENTATION-CHANGELOG-2026-08-28.md
  analyze_gdp_cem_e19_reproduction.py
  audit_gdp_cem_e19_cube_generator_compat.py
  audit_gdp_cem_e19_data_overlap.py
  audit_gdp_cem_e19_lewm_identity.py
  audit_gdp_cem_e19_release.py
  audit_gdp_cem_e19_serialization_compat.py
  create_gdp_cem_e19_cells.py
  freeze_gdp_cem_e19.sh
  gdp_cem_e19_cube_generator_compat.py
  gdp_cem_e19_specs.py
  prepare_gdp_cem_e19_inputs.py
  run_gdp_cem_e19_analyze.slurm
  run_gdp_cem_e19_data_overlap_audit.slurm
  run_gdp_cem_e19_evaluate.slurm
  run_gdp_cem_e19_prepare.slurm
  run_gdp_cem_e19_release_audit.slurm
  run_gdp_cem_e19_runtime_preflight.slurm
  stage_gdp_cem_e19_checkpoints_login.sh
  submit_gdp_cem_e19.sh
  test_audit_gdp_cem_e19_data_overlap.py
  test_audit_gdp_cem_e19_release.py
  test_audit_gdp_cem_e19_serialization_compat.py
  test_gdp_cem_e19_cube_generator_compat.py
  test_gdp_cem_e19_specs.py
  validate_gdp_cem_e19_cell.py
)
SHIM_FILES=(jepa.py module.py)

STAGED_ROOT=$(cd "${STAGED_ROOT}" && pwd -P)
OFFICIAL_SAGE=$(cd "${OFFICIAL_SAGE}" && pwd -P)
LEWM_RUNTIME=$(cd "${LEWM_RUNTIME}" && pwd -P)
mkdir -p "${OUTPUT_PARENT}"
OUTPUT_PARENT=$(cd "${OUTPUT_PARENT}" && pwd -P)

test -f "${ENV_DIR}/E19-ENVIRONMENT-LOCK.txt"
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null
test "$(git -C "${OFFICIAL_SAGE}" rev-parse HEAD)" = "${COMMIT}"
test "$(git -C "${OFFICIAL_SAGE}" rev-parse 'HEAD^{tree}')" = "${TREE}"
test -z "$(git -C "${OFFICIAL_SAGE}" status --porcelain --untracked-files=all)"
git -C "${OFFICIAL_SAGE}" fsck --no-dangling >/dev/null
test "$(git -C "${LEWM_RUNTIME}" rev-parse HEAD)" = "${LEWM_RUNTIME_COMMIT}"
test "$(git -C "${LEWM_RUNTIME}" rev-parse 'HEAD^{tree}')" = "${LEWM_RUNTIME_TREE}"
test -z "$(git -C "${LEWM_RUNTIME}" status --porcelain --untracked-files=no)"
git -C "${LEWM_RUNTIME}" fsck --no-dangling >/dev/null
for file in "${FILES[@]}"; do
  test -f "${STAGED_ROOT}/${file}"
done
for file in "${SHIM_FILES[@]}"; do
  test -f "${STAGED_ROOT}/e19_lewm_serialization_compat/${file}"
done

BUILD=$(mktemp -d "${OUTPUT_PARENT}/.gdp-cem-e19-freeze.XXXXXXXX")
cleanup() {
  if [[ -n "${BUILD:-}" && -d "${BUILD}" ]]; then
    case "${BUILD}" in
      "${OUTPUT_PARENT}"/.gdp-cem-e19-freeze.*) rm -rf -- "${BUILD}" ;;
      *) printf 'refusing unsafe cleanup target: %s\n' "${BUILD}" >&2 ;;
    esac
  fi
}
trap cleanup EXIT

for file in "${FILES[@]}"; do
  cp -- "${STAGED_ROOT}/${file}" "${BUILD}/${file}"
done
mkdir -p "${BUILD}/lewm-serialization-compat"
for file in "${SHIM_FILES[@]}"; do
  cp -- "${STAGED_ROOT}/e19_lewm_serialization_compat/${file}" \
    "${BUILD}/lewm-serialization-compat/${file}"
done
cp -a -- "${OFFICIAL_SAGE}" "${BUILD}/official-sage"
mkdir -p "${BUILD}/lewm-runtime"
git -C "${LEWM_RUNTIME}" archive --format=tar HEAD \
  | tar -xf - -C "${BUILD}/lewm-runtime"
test -f "${BUILD}/lewm-runtime/jepa.py"
test -f "${BUILD}/lewm-runtime/module.py"

export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export PYTHONPATH=${BUILD}/lewm-serialization-compat:${BUILD}:${BUILD}/official-sage:${BUILD}/lewm-runtime
export E19_SAGE_ROOT=${BUILD}/official-sage
"${ENV_DIR}/bin/python" "${BUILD}/create_gdp_cem_e19_cells.py" \
  --output "${BUILD}/E19-CELLS.tsv"
test "$(wc -l < "${BUILD}/E19-CELLS.tsv")" -eq 181

"${ENV_DIR}/bin/python" - "${BUILD}" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
for path in sorted(root.glob("*.py")):
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY
find "${BUILD}" -maxdepth 1 -type f \
  \( -name '*.sh' -o -name '*.slurm' \) -exec bash -n '{}' ';'

"${ENV_DIR}/bin/python" -m pytest -q -p no:cacheprovider \
  "${BUILD}/test_gdp_cem_e19_specs.py" \
  "${BUILD}/test_audit_gdp_cem_e19_release.py" \
  "${BUILD}/test_audit_gdp_cem_e19_data_overlap.py" \
  "${BUILD}/test_audit_gdp_cem_e19_serialization_compat.py" \
  "${BUILD}/test_gdp_cem_e19_cube_generator_compat.py" \
  > "${BUILD}/wrapper-tests.txt"
"${ENV_DIR}/bin/python" -m pytest -q -p no:cacheprovider \
  "${BUILD}/official-sage/tests" > "${BUILD}/upstream-tests.txt"
grep -Eq '^7 passed(, [0-9]+ warnings?)? in [0-9.]+s$' \
  "${BUILD}/upstream-tests.txt"
test -z "$(git -C "${BUILD}/official-sage" status --porcelain --untracked-files=all)"

"${ENV_DIR}/bin/python" "${BUILD}/audit_gdp_cem_e19_serialization_compat.py" \
  --pair "pusht=${ROOT}/data/stablewm/pusht/lewm_object.ckpt,${ROOT}/data/stablewm/pusht/lewm_hf_22b330c_object.ckpt" \
  --pair "cube=${ROOT}/data/stablewm/cube/lewm_object.ckpt,${ROOT}/data/stablewm/cube/lewm_hf_b0747c5_object.ckpt" \
  --output "${BUILD}/LEWM-SERIALIZATION-COMPAT-PREFLIGHT.json"

"${ENV_DIR}/bin/python" - "${BUILD}" "${ENV_DIR}" "${COMMIT}" "${TREE}" \
  "${LEWM_RUNTIME_COMMIT}" "${LEWM_RUNTIME_TREE}" "${PROTOCOL}" <<'PY'
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


root = Path(sys.argv[1])
environment = Path(sys.argv[2])
payload = {
    "kind": "gdp_cem_e19_immutable_snapshot_preflight",
    "official_sage_commit": sys.argv[3],
    "official_sage_tree": sys.argv[4],
    "lewm_runtime_commit": sys.argv[5],
    "lewm_runtime_tree": sys.argv[6],
    "lewm_serialization_compat_preflight_sha256": digest(
        root / "LEWM-SERIALIZATION-COMPAT-PREFLIGHT.json"
    ),
    "lewm_serialization_compat_jepa_sha256": digest(
        root / "lewm-serialization-compat/jepa.py"
    ),
    "lewm_serialization_compat_module_sha256": digest(
        root / "lewm-serialization-compat/module.py"
    ),
    "cube_generator_compat_sha256": digest(
        root / "gdp_cem_e19_cube_generator_compat.py"
    ),
    "protocol_sha256": digest(root / sys.argv[7]),
    "cell_manifest_sha256": digest(root / "E19-CELLS.tsv"),
    "cell_count": 180,
    "wrapper_tests_sha256": digest(root / "wrapper-tests.txt"),
    "upstream_tests_sha256": digest(root / "upstream-tests.txt"),
    "environment_lock_sha256": digest(environment / "E19-ENVIRONMENT-LOCK.txt"),
    "environment_freeze_sha256": digest(environment / "pip-freeze.txt"),
    "official_source_modified": False,
    "performance_metric_read": False,
    "protected_metric_artifact_read": False,
    "d5_read": False,
}
(root / "FREEZE-AUDIT.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

(cd "${BUILD}" && {
  find . -type f ! -path './official-sage/.git/*' \
    ! -name SOURCE-MANIFEST.sha256 -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 sha256sum > SOURCE-MANIFEST.sha256
  sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null
})
SOURCE_HASH=$(sha256sum "${BUILD}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
DESTINATION=${OUTPUT_PARENT}/gdp-cem-e19-${SOURCE_HASH:0:16}
test ! -e "${DESTINATION}"
mv -- "${BUILD}" "${DESTINATION}"
BUILD=
chmod -R a-w "${DESTINATION}"
test ! -w "${DESTINATION}"
(cd "${DESTINATION}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
printf 'snapshot=%s\nsource_manifest_sha256=%s\nprotocol_sha256=%s\n' \
  "${DESTINATION}" "${SOURCE_HASH}" \
  "$(sha256sum "${DESTINATION}/${PROTOCOL}" | cut -d' ' -f1)"
