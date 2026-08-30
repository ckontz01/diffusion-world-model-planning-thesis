#!/usr/bin/env bash
set -euo pipefail

STAGED_ROOT=${1:?usage: freeze_gdp_cem_e19_d2.sh STAGED_ROOT PARENT_SNAPSHOT OUTPUT_PARENT}
PARENT_SNAPSHOT=${2:?usage: freeze_gdp_cem_e19_d2.sh STAGED_ROOT PARENT_SNAPSHOT OUTPUT_PARENT}
OUTPUT_PARENT=${3:?usage: freeze_gdp_cem_e19_d2.sh STAGED_ROOT PARENT_SNAPSHOT OUTPUT_PARENT}
ROOT=/lustreFS/data/superworld/ckontzias/thesis
ENV_DIR=${ROOT}/envs/sage-official-py310-torch251-cu121
PARENT_RUN=${ROOT}/experiments/gdp-cem-e19/discrepancy-diagnostic-run-20260829-e347bc08
E19_RUN=${ROOT}/experiments/gdp-cem-e19/native-reproduction-run-20260828-9f549988
PARENT_SOURCE_SHA=e347bc087381ecf0902581e8225165dbd64c887eba661b74b064c09d4e13d7fa
PARENT_PROTOCOL_SHA=e420dca314038141caa30cadf0fe67ba649e53803d393e85a52c5a87a321f319
LEGACY_ANALYZER_SHA=3ddecca36b538509a7664dd5bfdaa12fd6ae007e788a909c4a01f0a11811c710
PARENT_SPECS_SHA=0fc796ef859d56cea7c7e8c0c59ec040709794a974dfc51d8e34b5a98f1ff888
PARENT_TRACER_SHA=d7868498b3dcd77efbf7e7d57f55f2f6a8b1097070b3c90632163205b7a83589
SAGE_COMMIT=8219029fd52e89157e05aebb998ab26f0ef46966
SAGE_TREE=0c64066eeac97c27fee382c1879bb26968b3fd56
PROTOCOL=ACID-ALTERNATIVE-E19-D2-METHOD-AWARE-DISCREPANCY-REANALYSIS-PROTOCOL-2026-08-30.md

FILES=(
  "${PROTOCOL}"
  E19-D2-IMPLEMENTATION-CHANGELOG-2026-08-30.md
  analyze_gdp_cem_e19_d2.py
  freeze_gdp_cem_e19_d2.sh
  gdp_cem_e19_d2_specs.py
  gdp_cem_e19_d2_validity.py
  run_gdp_cem_e19_d2_analyze.slurm
  run_gdp_cem_e19_d2_validity.slurm
  submit_gdp_cem_e19_d2.sh
  test_gdp_cem_e19_d2_validity.py
)
PARENT_FILES=(
  analyze_gdp_cem_e19_discrepancy.py
  gdp_cem_e19_discrepancy_specs.py
  test_analyze_gdp_cem_e19_discrepancy.py
  trace_gdp_cem_e19_discrepancy.py
)

STAGED_ROOT=$(cd "${STAGED_ROOT}" && pwd -P)
PARENT_SNAPSHOT=$(cd "${PARENT_SNAPSHOT}" && pwd -P)
mkdir -p "${OUTPUT_PARENT}"
OUTPUT_PARENT=$(cd "${OUTPUT_PARENT}" && pwd -P)

test "${PARENT_SNAPSHOT}" = \
  "${ROOT}/snapshots/gdp-cem-e19-discrepancy-e347bc087381ecf0"
test ! -w "${PARENT_SNAPSHOT}"
test "$(sha256sum "${PARENT_SNAPSHOT}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)" = \
  "${PARENT_SOURCE_SHA}"
(cd "${PARENT_SNAPSHOT}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
test "$(sha256sum "${PARENT_SNAPSHOT}/ACID-ALTERNATIVE-E19-OFFICIAL-SAGE-DISCREPANCY-DIAGNOSTIC-PROTOCOL-2026-08-29.md" | cut -d' ' -f1)" = \
  "${PARENT_PROTOCOL_SHA}"
test "$(sha256sum "${PARENT_SNAPSHOT}/analyze_gdp_cem_e19_discrepancy.py" | cut -d' ' -f1)" = \
  "${LEGACY_ANALYZER_SHA}"
test "$(sha256sum "${PARENT_SNAPSHOT}/gdp_cem_e19_discrepancy_specs.py" | cut -d' ' -f1)" = \
  "${PARENT_SPECS_SHA}"
test "$(sha256sum "${PARENT_SNAPSHOT}/trace_gdp_cem_e19_discrepancy.py" | cut -d' ' -f1)" = \
  "${PARENT_TRACER_SHA}"
test "$(git -C "${PARENT_SNAPSHOT}/official-sage" rev-parse HEAD)" = "${SAGE_COMMIT}"
test "$(git -C "${PARENT_SNAPSHOT}/official-sage" rev-parse 'HEAD^{tree}')" = "${SAGE_TREE}"
test -z "$(git -C "${PARENT_SNAPSHOT}/official-sage" status --porcelain --untracked-files=all)"
sha256sum -c "${ENV_DIR}/sha256.txt" >/dev/null

for sentinel in 0 1 2 3 4; do
  for repeat in 0 1; do
    (cd "${PARENT_RUN}/sentinels/s${sentinel}/r${repeat}" && \
      sha256sum -c sha256.txt >/dev/null)
  done
done
(cd "${PARENT_RUN}/comparison" && sha256sum -c sha256.txt >/dev/null)
test -d "${PARENT_RUN}/analysis"
test -d "${E19_RUN}/analysis"

for file in "${FILES[@]}"; do
  test -f "${STAGED_ROOT}/${file}"
done
for file in "${PARENT_FILES[@]}"; do
  test -f "${PARENT_SNAPSHOT}/${file}"
done

BUILD=$(mktemp -d "${OUTPUT_PARENT}/.gdp-cem-e19-d2-freeze.XXXXXXXX")
cleanup() {
  if [[ -n "${BUILD:-}" && -d "${BUILD}" ]]; then
    case "${BUILD}" in
      "${OUTPUT_PARENT}"/.gdp-cem-e19-d2-freeze.*) rm -rf -- "${BUILD}" ;;
      *) printf 'refusing unsafe cleanup target: %s\n' "${BUILD}" >&2 ;;
    esac
  fi
}
trap cleanup EXIT

for file in "${FILES[@]}"; do
  cp -- "${STAGED_ROOT}/${file}" "${BUILD}/${file}"
done
for file in "${PARENT_FILES[@]}"; do
  cp -- "${PARENT_SNAPSHOT}/${file}" "${BUILD}/${file}"
done

export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0
export PYTHONPATH=${BUILD}
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
  "${BUILD}/test_analyze_gdp_cem_e19_discrepancy.py" \
  "${BUILD}/test_gdp_cem_e19_d2_validity.py" \
  > "${BUILD}/wrapper-tests.txt"
grep -Eq '^9 passed in [0-9.]+s$' "${BUILD}/wrapper-tests.txt"

"${ENV_DIR}/bin/python" - "${BUILD}" "${ENV_DIR}" "${PARENT_SNAPSHOT}" \
  "${PARENT_SOURCE_SHA}" "${PARENT_PROTOCOL_SHA}" "${LEGACY_ANALYZER_SHA}" \
  "${SAGE_COMMIT}" "${SAGE_TREE}" "${PROTOCOL}" <<'PY'
from __future__ import annotations

import hashlib
import json
import re
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
wrapper_text = (root / "wrapper-tests.txt").read_text(encoding="utf-8")
match = re.search(r"(\d+) passed", wrapper_text)
if match is None:
    raise RuntimeError("wrapper-test pass count missing")
payload = {
    "kind": "gdp_cem_e19_d2_method_aware_analyzer_snapshot_preflight",
    "parent_snapshot": sys.argv[3],
    "parent_source_manifest_sha256": sys.argv[4],
    "parent_protocol_sha256": sys.argv[5],
    "parent_analyzer_sha256": sys.argv[6],
    "official_sage_commit": sys.argv[7],
    "official_sage_tree": sys.argv[8],
    "d2_protocol_sha256": digest(root / sys.argv[9]),
    "wrapper_test_count": int(match.group(1)),
    "wrapper_tests_sha256": digest(root / "wrapper-tests.txt"),
    "environment_lock_sha256": digest(environment / "E19-ENVIRONMENT-LOCK.txt"),
    "environment_freeze_sha256": digest(environment / "pip-freeze.txt"),
    "raw_sentinel_manifest_count": 10,
    "raw_comparison_manifest_valid": True,
    "episode_rerun": False,
    "old_analyzer_output_read": False,
    "only_correction": "method_aware_history_latent_expectation",
    "e19_decision_preserved": "stop_native_reproduction_failed",
    "parent_diagnostic_preserved_failed": True,
    "planner_parameter_modified": False,
    "expected_values_modified": False,
    "tolerance_modified": False,
    "manifest_modified": False,
    "protected_metric_artifact_read": False,
    "e18_vs_sage_comparison_run": False,
    "d5_read": False,
    "author_contact_performed": False,
}
(root / "FREEZE-AUDIT.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY

(cd "${BUILD}" && {
  find . -type f ! -name SOURCE-MANIFEST.sha256 -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 sha256sum > SOURCE-MANIFEST.sha256
  sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null
})
SOURCE_HASH=$(sha256sum "${BUILD}/SOURCE-MANIFEST.sha256" | cut -d' ' -f1)
DESTINATION=${OUTPUT_PARENT}/gdp-cem-e19-d2-${SOURCE_HASH:0:16}
test ! -e "${DESTINATION}"
mv -- "${BUILD}" "${DESTINATION}"
BUILD=
chmod -R a-w "${DESTINATION}"
test ! -w "${DESTINATION}"
(cd "${DESTINATION}" && sha256sum -c SOURCE-MANIFEST.sha256 >/dev/null)
printf 'snapshot=%s\nsource_manifest_sha256=%s\nprotocol_sha256=%s\n' \
  "${DESTINATION}" "${SOURCE_HASH}" \
  "$(sha256sum "${DESTINATION}/${PROTOCOL}" | cut -d' ' -f1)"
